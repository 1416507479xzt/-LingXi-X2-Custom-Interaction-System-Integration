"""Synthetic regression of observed dialogue issues; no ROS, TTS or robot calls."""
import argparse
import asyncio
from datetime import datetime
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
sys.path.insert(0, str(ROOT))
from x2_agent.agent_config import AgentConfig
from x2_agent.life_assistance import LOCAL_TIME, load_context
from x2_agent.llm import LlmClient
from x2_agent.model_dialogue import ModelDialogue, generate_dialogue
from x2_agent.presentation import capabilities


async def check(output):
    config = AgentConfig.from_env(llm_model='doubao-seed-2-0-mini-260428')
    client = LlmClient(config.ark_api_url)
    rows = []
    scenarios = {
        'healthy_and_correction': ['今天感觉不错', '你在说什么东西啊？', '你真是个呆子。'],
        'medicine_to_daily_schedule': ['降压药该怎么吃', '今天有什么注意事项', '我问的是今天的日常安排和提醒', '降压药有什么注意事项'],
        'contextual_gestures': ['请向我挥挥手', '请用双手给我比个心', '我今天按计划完成了阅读和散步，感觉很开心。'],
    }
    try:
        for scenario, utterances in scenarios.items():
            memory = ModelDialogue()
            memory.begin()
            if scenario != 'healthy_and_correction':
                memory.interview_active = False
            for utterance in utterances:
                context = {**memory.context(),
                    'capabilities': capabilities(backend='aimdk', enable_motion=True),
                    'life_assistance': load_context(now=datetime(2026, 11, 19, 16, 0, tzinfo=LOCAL_TIME))}
                start = time.perf_counter()
                answer = await generate_dialogue(client, utterance, context, config.llm_model, config.ark_key)
                rows.append(dict(scenario=scenario, user=utterance, answer=answer,
                    generation_ms=round((time.perf_counter()-start)*1000)))
                if answer:
                    memory.commit(utterance, answer)
                print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    finally:
        await client.close()
    report = dict(scope=__doc__, model=config.llm_model, cases=rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='允许付费云端文本测试，10轮，可能有有界修复请求')
    parser.add_argument('--output', type=Path, default=ROOT/'logs'/'observed_dialogue_live.json')
    args = parser.parse_args()
    if not args.live:
        parser.error('--live is required')
    asyncio.run(check(args.output))
