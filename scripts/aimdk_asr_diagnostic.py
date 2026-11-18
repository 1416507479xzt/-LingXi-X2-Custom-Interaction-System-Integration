"""Compare several real X2 VAD segments without saving or playing audio.

Run only on the robot PC2 after loading its AimDK ROS environment. This
diagnostic does not change interaction mode or call robot control services.
"""

import argparse
import array
import asyncio
import os
from pathlib import Path
from collections import Counter, deque
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

from x2_agent.aimdk_audio import VadAssembler
from x2_agent.config import load_env


def pcm_levels(pcm):
    samples = array.array("h")
    samples.frombytes(pcm[:len(pcm) // 2 * 2])
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return 0, 0
    peak = max(abs(value) for value in samples)
    rms = int((sum(value * value for value in samples) / len(samples)) ** 0.5)
    return rms, peak


async def recognize_with_capture(recognition, spin_once, ros_ok):
    """Keep draining DDS while the cloud coroutine waits for network I/O."""
    task = asyncio.create_task(recognition)
    try:
        while not task.done():
            if not ros_ok():
                raise RuntimeError("ROS 已停止")
            spin_once()
            await asyncio.sleep(0.005)
        return await task
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", help="本地密钥配置路径；默认项目根目录 .env")
    parser.add_argument("--duration", type=float, default=60,
                        help="overall listening limit in seconds")
    parser.add_argument("--count", type=int, default=4,
                        help="maximum VAD segments to inspect")
    parser.add_argument("--stream-id", type=int, default=1)
    parser.add_argument("--wake-hotwords", action="store_true",
                        help="为本次识别请求启用灵犀热词提示")
    args = parser.parse_args(argv)
    load_env(args.env_file)
    if args.duration <= 0 or args.count < 1 or args.count > 10 or args.stream_id < 0:
        parser.error("duration must be positive; count 1..10; stream-id nonnegative")
    if args.wake_hotwords:
        os.environ["DOUBAO_ASR_HOTWORDS"] = '["灵犀"]'
    from x2_agent.asr import configured_hotwords
    try:
        words = configured_hotwords()
    except ValueError as exc:
        parser.error(str(exc))
    print("ASR 热词设置：%s" % ("、".join(words) if words else "关闭（基线）"),
          flush=True)
    speech_key = os.environ.get("DOUBAO_SPEECH_API_KEY", "")
    if not speech_key:
        raise SystemExit("缺少 DOUBAO_SPEECH_API_KEY；未订阅麦克风")

    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from aimdk_msgs.msg import ProcessedAudioOutput
    from x2_agent.asr import asr_transcribe

    collector = VadAssembler(stream_id=args.stream_id)
    pending = deque()
    states = Counter()
    received_bytes = Counter()
    complete_count = 0
    rclpy.init()
    node = rclpy.create_node("eldercare_asr_diagnostic")
    qos = QoSProfile(depth=50, reliability=ReliabilityPolicy.BEST_EFFORT,
                     durability=DurabilityPolicy.VOLATILE)

    def on_audio(msg):
        nonlocal complete_count
        states[(msg.stream_id, msg.audio_vad_state.value)] += 1
        received_bytes[msg.stream_id] += len(msg.audio_data)
        if msg.stream_id == args.stream_id and msg.audio_vad_state.value == 1:
            print("VAD BEGIN：本包%d字节；请连续说完目标句，随后安静等待。" %
                  len(msg.audio_data), flush=True)
        if (msg.stream_id == args.stream_id and msg.audio_vad_state.value == 2 and
                states[(msg.stream_id, 2)] == 1):
            print("VAD PROCESSING：已收到后续音频。", flush=True)
        if msg.stream_id == args.stream_id and msg.audio_vad_state.value == 3:
            print("VAD END：收到片段结束事件。", flush=True)
        segment = collector.feed(msg.stream_id, msg.audio_vad_state.value, msg.audio_data)
        if segment is not None and segment.pcm:
            complete_count += 1
            if len(pending) >= 4:
                pending.popleft()
                print("诊断积压超过4段，丢弃最旧片段；本轮需重新对照。", flush=True)
            pending.append(segment)

    node.create_subscription(ProcessedAudioOutput, "/agent/process_audio_output",
                             on_audio, qos)
    resource_id = os.environ.get("DOUBAO_ASR_RESOURCE_ID",
                                 "volc.seedasr.sauc.duration")
    deadline = time.monotonic() + args.duration
    print("只读监听最多 %.0f 秒、最多 %d 段；不保存录音。" %
          (args.duration, args.count), flush=True)
    try:
        for index in range(1, args.count + 1):
            print("等待第 %d 段语音；看到此行后再说话。" % index, flush=True)
            while rclpy.ok() and not pending and time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=0.1)
            if not pending:
                print("到时或 ROS 已停止；本次没有更多完整 VAD 片段。", flush=True)
                break
            segment = pending.popleft()
            rms, peak = pcm_levels(segment.pcm)
            print("第 %d 段：%.2f 秒PCM，VAD接收历时%.2f秒，%d 包，RMS=%d，峰值=%d" %
                  (index, segment.audio_seconds, segment.elapsed_seconds,
                   segment.packet_count, rms, peak),
                  flush=True)
            print("正在识别，麦克风仍持续接收；请等下一次等待提示再说下一句。", flush=True)
            try:
                result = asyncio.run(recognize_with_capture(
                    asr_transcribe(segment.pcm, speech_key, resource_id),
                    lambda: rclpy.spin_once(node, timeout_sec=0), rclpy.ok))
                print("第 %d 段 ASR：%s" % (index, result or "<空>"), flush=True)
            except Exception as exc:
                print("第 %d 段 ASR 错误：%s: %s" %
                      (index, type(exc).__name__, exc), flush=True)
    except KeyboardInterrupt:
        print("用户停止诊断。", flush=True)
    finally:
        print("VAD统计：%s；各流总字节=%s；完整非空片段=%d；超长丢弃=%d" %
              (dict(states), dict(received_bytes), complete_count, collector.discarded),
              flush=True)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
