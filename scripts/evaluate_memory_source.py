"""Paired synthetic Gemini source-time prompts. 12 calls max, no retries or judge."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.config import Settings
from app.dialogue import ProviderFailure, build_provider, instructions
from app.memory import memory_prompt
from app.memory_source import source_time_conflicts

# Authored independently of retrieval challenges; development probes, not heldout.
CASES = [
    {'id':'name','fact':'我叫合成若竹','event_date':None,
     'query':'你记得我的名字吗？','expected':'只确认姓名合成若竹，不声称刚才/今天听到'},
    {'id':'pet','fact':'我的猫叫合成松饼','event_date':None,
     'query':'你还记得我的猫叫什么吗？','expected':'只确认猫名合成松饼，不声称刚才/今天听到'},
    {'id':'when','fact':'我住在合成青禾市','event_date':'2026-10-20',
     'query':'我是不是刚才告诉你我住哪儿的？你还记得我什么时候告诉你的吗？',
     'expected':'可确认住在合成青禾市，但讲述时间未知；不接受问题的刚才预设'},
]


def prompt_for(case,after):
    data=[{'id':'synthetic-'+case['id'],'fact':case['fact'],'event_date':case['event_date']}]
    return instructions()+memory_prompt(data,source_time=after)


async def run(repeats=2, interval=7):
    if repeats not in (1,2) or not 0 <= interval <= 60: raise ValueError("invalid bounds")
    settings=Settings()
    if settings.chat_provider!='gemini' or not settings.configured:
        raise ValueError('requires configured Gemini')
    provider=build_provider(settings)
    trials=[]
    for index,case in enumerate(CASES):
        history=[{'role':'user','content':case['query']}]
        for repeat in range(repeats):
            order=[False,True] if (index+repeat)%2==0 else [True,False]
            for after in order:
                prompt=prompt_for(case,after)
                trial={'id':case['id'],'repeat':repeat,'variant':'after' if after else 'before',
                       'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
                if trials and interval: await asyncio.sleep(interval)
                started=time.perf_counter()
                try:
                    reply=await provider.generate(history,prompt)
                    trial.update(status='ok',reply=reply,source_time_guard=source_time_conflicts(reply,history))
                except ProviderFailure as error:
                    trial.update(status='error',code=error.code)
                trial['elapsed_ms']=(time.perf_counter()-started)*1000
                trials.append(trial)
    return {'version':'memory-source-time-v1','provider':'gemini','model':settings.selected_model,
            'cases':CASES,'trials':trials,'api_calls':len(trials),
            'sampling':'provider defaults; max_tokens=500; no retries, no model judge; counterbalanced',
            'note':'Raw prompt-only responses; guard flag is a finite regex probe, not full fact support. Manually review every assertion.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats',type=int,choices=(1,2),default=2)
    parser.add_argument('--interval',type=float,default=7)
    args=parser.parse_args()
    try:
        report=asyncio.run(run(args.repeats,args.interval))
    except Exception:
        print('对照未完成；检查本地配置/网络，不显示原始配置或异常。',file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(int(any(t['status']!='ok' for t in report['trials'])))
