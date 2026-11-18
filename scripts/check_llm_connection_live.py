"""Paid Mini connection timing probe; no robot, ASR or TTS, no credentials printed."""
import argparse
import asyncio
import json
import logging
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from x2_agent.agent_config import AgentConfig
from x2_agent.llm import LlmClient


async def run(args):
    config = AgentConfig.from_env()
    client = LlmClient(config.ark_api_url)
    try:
        if args.keepalive:
            client.start_keepalive(config.ark_key)
        try:
            await client.warm(config.ark_key)
        except Exception as exc:
            print("预连接未完成：" + type(exc).__name__)
        for index in range(args.rounds):
            if index:
                print("空闲等待 %.1f 秒，随后执行相同测试请求。" % args.idle_seconds, flush=True)
                await asyncio.sleep(args.idle_seconds)
            started = time.perf_counter()
            first = None
            async for kind, value in client.stream("只回复两个字：收到。", [{"role": "user", "content": "连接计时测试"}],
                                                  config.llm_model, config.ark_key):
                if kind == "text" and value and first is None:
                    first = (time.perf_counter() - started) * 1000
            print(json.dumps({"round": index + 1, "model": config.llm_model,
                              "keepalive": args.keepalive, "first_token_ms": round(first) if first is not None else None,
                              "total_ms": round((time.perf_counter() - started) * 1000)}, ensure_ascii=False), flush=True)
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--keepalive", action="store_true")
    parser.add_argument("--rounds", type=int, choices=range(1, 4), default=2)
    parser.add_argument("--idle-seconds", type=float, default=25)
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required; this uses the configured API account")
    if not 0 <= args.idle_seconds <= 55:
        parser.error("--idle-seconds must be between 0 and 55")
    logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    asyncio.run(run(args))
