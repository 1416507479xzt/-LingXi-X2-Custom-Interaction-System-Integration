"""Paid, text-only comparison using fixed synthetic context; no robot or TTS."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from x2_agent.agent_config import AgentConfig
from x2_agent.life_assistance import load_context
from x2_agent.llm import LlmClient
from x2_agent.model_dialogue import ModelDialogue, generate_dialogue
from x2_agent.presentation import capabilities


class CountedClient:
    def __init__(self, client):
        self.client = client
        self.requests = 0
        self.drafts = []

    async def stream(self, *args, **kwargs):
        self.requests += 1
        parts = []
        async for kind, chunk in self.client.stream(*args, **kwargs):
            if kind == "text" and isinstance(chunk, str):
                parts.append(chunk)
            yield kind, chunk
        try:
            self.drafts.append(json.loads("".join(parts)).get("reply"))
        except (ValueError, AttributeError):
            self.drafts.append(None)


async def run(args):
    config = AgentConfig.from_env()
    client = LlmClient(config.ark_api_url)
    counted = CountedClient(client)
    previous = "颈部避免长时间保持同一姿势；腰背如能活动，在不加重疼痛的范围内维持日常活动、避免久卧，若近期摔倒或扭伤，请联系医护。"
    context = {**ModelDialogue().context(), "health_rounds": 2,
               "capabilities": capabilities(backend="none"),
               "life_assistance": load_context(),
               "verbatim_turns": [
                   {"user": "今天过得不错", "assistant": "有没有哪里不舒服？"},
                   {"user": "我没有哪里不舒服", "assistant": "有任何不适随时告诉我。"},
                   {"user": "我倒是脖子和腰有点酸", "assistant": previous}]}
    rows = []
    try:
        for trial in range(args.trials):
            for utterance in ("有什么好的缓解办法吗？", "刚才没听清，再说一遍。", "你还记得我刚才哪里不舒服吗？"):
                counted.requests = 0
                counted.drafts = []
                started = time.perf_counter()
                answer = await generate_dialogue(counted, utterance, context,
                                                 config.llm_model, config.ark_key)
                row = {"trial": trial + 1, "model": config.llm_model,
                       "user": utterance, "previous_reply": previous,
                       "answer": answer, "requests": counted.requests, "draft_replies": counted.drafts,
                       "generation_ms": round((time.perf_counter() - started) * 1000),
                       "reply_chars": len(answer["reply"]) if answer else 0}
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    finally:
        await client.close()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow paid cloud calls; read local .env")
    parser.add_argument("--trials", type=int, choices=range(1, 4), default=1)
    parser.add_argument("--output", type=Path, help="Save synthetic replies and timings, never credentials")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required; this uses the configured API account")
    asyncio.run(run(args))
