"""Paid, text-only Mini planning check. Never imports ROS or dispatches actions."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor'))
sys.path.insert(0,str(ROOT))
from x2_agent.agent_config import AgentConfig
from x2_agent.llm import LlmClient
from x2_agent.model_dialogue import ModelDialogue, generate_dialogue
from x2_agent.presentation import capabilities

CASES=(
    ('greeting','你好灵犀',None),
    ('left_wave','请用左手挥挥手，右手不要动。',{'wave_left'}),
    ('clap','请给我鼓鼓掌。',{'clap'}),
    ('heart','请用双手比个心。',{'heart_both'}),
    ('salute','请敬一个右手礼。',{'salute_right'}),
    ('refuse','别做任何动作，只跟我说一句鼓励的话。',{None}),
    ('fatigue','我今天有点疲惫。',None),
    ('autonomous_encouragement','我今天按计划完成了阅读和散步，感觉很开心。',None),
    ('invited_handshake','我愿意和您握手，请伸出右手。',{'shake_right'}),
    ('explicit_performance','请做一个动感光波动作。',{'lightwave'}))


async def check(output):
    config=AgentConfig.from_env(llm_model='doubao-seed-2-0-mini-260428')
    client=LlmClient(config.ark_api_url)
    rows=[]
    try:
        for name,utterance,expected in CASES:
            context={**ModelDialogue().context(), 'turn_kind':'greeting' if name=='greeting' else 'dialogue',
                     'capabilities':capabilities(backend='aimdk',enable_motion=True)}
            started=time.perf_counter()
            answer=await generate_dialogue(client,utterance,context,config.llm_model,config.ark_key)
            row={'case':name,'user':utterance,'answer':answer,
                 'generation_ms':round((time.perf_counter()-started)*1000),
                 'valid':answer is not None,
                 'explicit_gesture_match':None if expected is None else
                     bool(answer is not None and answer.get('gesture') in expected)}
            rows.append(row)
            print(json.dumps(row,ensure_ascii=False),flush=True)
    finally:
        await client.close()
    report={'scope':'Synthetic text planning only; no robot, TTS or ROS calls',
            'model':config.llm_model,'cases':rows,
            'valid_count':sum(row['valid'] for row in rows),
            'explicit_match_count':sum(row['explicit_gesture_match'] is True for row in rows),
            'explicit_case_count':sum(row['explicit_gesture_match'] is not None for row in rows)}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='cases'},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='允许付费云端文本调用，最多约20次模型请求')
    parser.add_argument('--output',type=Path,default=ROOT/'logs'/'presentation_autonomy_live.json')
    args=parser.parse_args()
    if not args.live:
        parser.error('--live is required')
    asyncio.run(check(args.output))
