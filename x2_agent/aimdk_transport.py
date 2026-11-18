"""Local AimDK transport exposing the existing Agent's gateway event contract.

The dialogue, ASR, TTS and stage logic stay in DoubaoAgent. This adapter
converts ROS VAD audio into start/append/commit frames (optionally live),
and routes the Agent's PCM output to the opt-in ROS player.
"""

import asyncio
import base64
from contextlib import suppress
import json
import logging
import time
import uuid

from .aimdk_audio import VadAssembler
from .aimdk_playback import AimdkPcmPlayer
from .aimdk_runtime import verify_audio_interfaces
from .gateway import T
from .aimdk_streaming import StreamingVadInput

logger = logging.getLogger("x2_agent")


class AimdkLocalTransport:
    def __init__(self, *, stream_id=1, idle_seconds=0, streaming=False):
        if idle_seconds != 0 and not 0.5 <= idle_seconds <= 5:
            raise ValueError("idle_seconds must be 0 or 0.5..5")
        try:
            import rclpy
            from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
            from aimdk_msgs.msg import ProcessedAudioOutput, AudioPlayback
            from aimdk_msgs.srv import RequestAudioFocus, AbandonAudioFocus
        except ImportError as exc:
            raise ValueError("AimDK 真机传输需要 PC2 的 rclpy 和机载 aimdk_msgs") from exc
        verify_audio_interfaces(ProcessedAudioOutput, AudioPlayback,
                                RequestAudioFocus, AbandonAudioFocus)
        self.ros = rclpy
        if not rclpy.ok():
            rclpy.init()
        self.node = rclpy.create_node("eldercare_vad_input")
        self.player = AimdkPcmPlayer()
        self.collector = VadAssembler(stream_id=stream_id)
        self.incoming = asyncio.Queue(maxsize=4)
        self._spin_task = None
        self._closed = False
        self._speaking = False
        self._playing = False
        self.idle_seconds = idle_seconds
        self._last_received = None
        self._live_frames = asyncio.Queue(maxsize=256)
        self._live = (StreamingVadInput(self._emit_live, stream_id=stream_id,
                                       idle_seconds=idle_seconds) if streaming else None)
        qos = QoSProfile(depth=50, reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE)
        self.node.create_subscription(ProcessedAudioOutput,
                                      "/agent/process_audio_output", self._on_audio, qos)

    def _on_audio(self, msg):
        if self._live is not None:
            if self._speaking:
                return
            try:
                self._live.feed(msg.stream_id, msg.audio_vad_state.value, msg.audio_data)
            except asyncio.QueueFull:
                self._abort_live_overflow()
            return
        if self._speaking:
            self.collector.reset()
            self._last_received = None
            return
        if msg.stream_id == self.collector.stream_id and msg.audio_vad_state.value in (1, 2, 3):
            self._last_received = time.monotonic()
        utterance = self.collector.feed(msg.stream_id, msg.audio_vad_state.value,
                                        msg.audio_data)
        self._queue_utterance(utterance)

    def _queue_utterance(self, utterance):
        if utterance is None or not utterance.pcm:
            return
        try:
            self.incoming.put_nowait(utterance.pcm)
        except asyncio.QueueFull:
            logger.warning("真机 VAD 队列已满，丢弃一段录音以免旧话延后播报")

    def _emit_live(self, frame):
        if self._live_frames.full():
            # Cancel the entire upload rather than recognizing a truncated turn.
            while not self._live_frames.empty():
                self._live_frames.get_nowait()
            self._live_frames.put_nowait({"type": T["a_cancel"]})
            raise asyncio.QueueFull
        self._live_frames.put_nowait(frame)
        if frame.get("boundary") == "idle_timeout":
            logger.warning("AimDK实时收音缺少END：停收%.1fs后提交%d字节",
                           self.idle_seconds, frame["pcmBytes"])

    def _abort_live_overflow(self):
        self._live.event_id = None
        self._live.cancel()
        self._live.blocked = True
        self._live.awaiting_reply = False
        logger.error("真机实时音频队列已满：取消本轮，等待新的BEGIN")

    def _check_idle(self, now=None):
        if getattr(self, "_live", None) is not None:
            try:
                self._live.check_idle(now)
            except asyncio.QueueFull:
                self._abort_live_overflow()
            return
        now = time.monotonic() if now is None else now
        if (not self.idle_seconds or self._speaking or self._last_received is None or
                now - self._last_received < self.idle_seconds):
            return
        self._last_received = None
        utterance = self.collector.take_pending(now)
        if utterance is not None:
            logger.warning("AimDK缺少VAD END：停收%.1fs，提交残留%.2fs PCM；"
                           "本轮边界为超时恢复，可能不完整",
                           self.idle_seconds, utterance.audio_seconds)
            self._queue_utterance(utterance)

    async def _spin(self):
        while not self._closed and self.ros.ok():
            self.ros.spin_once(self.node, timeout_sec=0)
            self._check_idle()
            await asyncio.sleep(0.005)

    async def __aenter__(self):
        self._spin_task = asyncio.create_task(self._spin())
        return self

    async def __aexit__(self, *_):
        self._closed = True
        try:
            if self._spin_task is not None:
                self._spin_task.cancel()
                with suppress(asyncio.CancelledError):
                    await self._spin_task
            await self.player.end()
        finally:
            self.node.destroy_node()
            self.player.close()

    def __aiter__(self):
        return self._frames()

    async def _frames(self):
        yield json.dumps({"type": T["sync"], "robotCid": "aimdk-local",
                          "state": "online", "callbackType": "audio2tts",
                          "controlActive": True, "audioActive": True})
        while not self._closed:
            if getattr(self, "_live", None) is not None:
                yield json.dumps(await self._live_frames.get())
                continue
            pcm = await self.incoming.get()
            if self._speaking:
                continue
            event_id = "aimdk-" + uuid.uuid4().hex[:12]
            yield json.dumps({"type": T["a_start"], "eventId": event_id})
            for offset in range(0, len(pcm), 6400):
                chunk = pcm[offset:offset + 6400]
                yield json.dumps({"type": T["a_append"], "eventId": event_id,
                                  "audio": base64.b64encode(chunk).decode("ascii")})
            yield json.dumps({"type": T["a_commit"], "eventId": event_id})

    async def send(self, raw):
        frame = json.loads(raw)
        ftype = frame.get("type")
        if ftype == T["tts_delta"]:
            if not self._playing:
                await self.player.begin()
                self._playing = True
                self._speaking = True
            await self.player.write(base64.b64decode(frame["audio"], validate=True))
        elif ftype == T["tts_done"]:
            if self._playing:
                try:
                    await self.player.end()
                finally:
                    self._playing = False
                    self._speaking = False
            if getattr(self, "_live", None) is not None:
                self._live.resume()
        elif ftype == T["error"]:
            if getattr(self, "_live", None) is not None:
                self._live.resume()
            logger.error("真机轮次失败: %s %s", frame.get("errorCode"),
                         frame.get("errorMsg"))
