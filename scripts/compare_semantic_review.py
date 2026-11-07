"""Bounded paired Gemini development comparison; --live required, no database."""
import argparse
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
import types

import httpx2
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.fact_support_evaluation import load_dataset
from app.semantic_review import ModelAnalysisProvider,INDEXED_PROMPT,evidence_bundle,review_reply

BASELINE='5aec504a079e2e8df4d88881225bfe70cfdeac63'
BASELINE_SHA='42d50f5de4978766937a433db9294d2f760cbff2f9303b2bee5384e565002c31'
IDS=('scene-stock-completed','place-english-changed','paraphrase-place-inference',
     'scene-conditional-expanded','place-correction-quote','source-current-paraphrase')


def baseline_provider():
    root=Path(__file__).resolve().parent.parent
    code=subprocess.check_output(['git','show',BASELINE+':app/semantic_review.py'],cwd=root)
    if hashlib.sha256(code).hexdigest()!=BASELINE_SHA:raise ValueError('baseline mismatch')
    name='app._frozen_review_baseline'
    module=types.ModuleType(name);module.__package__='app';sys.modules[name]=module
    # Only the fixed, hash-checked local repository revision, never user code.
    exec(compile(code,'<frozen-review-baseline>','exec'),module.__dict__)
    class BaselineAdapter(module.ModelAnalysisProvider):
        async def review(self,*args):
            return (await super().review(*args)).model_dump()
    return BaselineAdapter


def cases():
    data,digest=load_dataset()
    result=[]
    for id in IDS:
        case=next(c for c in data.cases if c.id==id)
        memories=[{'id':e.id,'fact':e.text,'event_date':e.event_date} for e in data.evidence
                  if e.id in case.evidence_ids and e.kind=='memory']
        result.append({'id':id,'query':case.query,'candidate':case.reply,'memories':memories,
                       'expected':'revise' if any(c.verdict in ('unsupported','contradicted') or c.form_violation for c in case.claims) else 'accept'})
    result += [
        {'id':'role-does-not-prove-messages','query':'你店里今天怎么样？','memories':[],
         'candidate':'店里具体的情况我没办法确定，也没收到什么新的消息。','expected':'revise'},
        {'id':'unknown-is-not-negative-stock','query':'你店里今天怎么样？','memories':[],
         'candidate':'店里现在的具体情况，我还不能确定。你想聊聊喜欢的书吗？','expected':'accept'},
    ]
    return result,digest


def summarize(rows):
    summary={}
    for name in ('baseline','indexed'):
        batch=[r for r in rows if r['variant']==name]
        elapsed=sorted(r['elapsed_seconds'] for r in batch)
        valid=[r for r in batch if r['status'] in ('accept','revise')]
        summary[name]={'attempts':len(batch),'usable':len(valid),'matched':sum(r['match'] for r in batch),
            'false_accept':sum(r['status']=='accept' and r['expected']=='revise' for r in batch),
            'false_revise':sum(r['status']=='revise' and r['expected']=='accept' for r in batch),
            'timeouts':sum(r['failure']=='timeout' for r in batch),
            'failures':dict(Counter(r['failure'] for r in batch if r['failure'])),
            'p50_seconds':statistics.median(elapsed) if elapsed else None,
            'usable_p50_seconds':statistics.median(r['elapsed_seconds'] for r in valid) if valid else None,
            'max_seconds':max(elapsed) if elapsed else None,
            'usage_observed':sum(r['usage'] is not None for r in batch),
            'prompt_tokens':sum((r['usage'] or {}).get('prompt_tokens',0) for r in batch),
            'completion_tokens':sum((r['usage'] or {}).get('completion_tokens',0) for r in batch)}
    return summary


async def compare(settings,*,repeats=2,interval=10):
    legacy=baseline_provider();fixtures,digest=cases();rows=[]
    for repetition in range(repeats):
        for index,case in enumerate(fixtures):
            # Alternate order between cases and repetitions; never retry failures.
            order=('baseline','indexed') if (index+repetition)%2==0 else ('indexed','baseline')
            history=[{'role':'user','content':case['query']}]
            evidence=evidence_bundle(history,case['memories'],None,None)
            for name in order:
                if rows:await asyncio.sleep(interval)
                usage=None;http_status=None
                async def capture(response):
                    nonlocal usage,http_status
                    http_status=response.status_code
                    await response.aread()
                    if response.status_code==200:
                        try:
                            source=response.json().get('usage',{})
                            usage={k:source[k] for k in ('prompt_tokens','completion_tokens','total_tokens')
                                   if type(source.get(k)) is int and source[k]>=0} or None
                        except (ValueError,TypeError):pass
                async with httpx2.AsyncClient(event_hooks={'response':[capture]}) as client:
                    provider=(legacy if name=='baseline' else ModelAnalysisProvider)(settings,client)
                    print(f'attempt {len(rows)+1} {repetition+1} {case["id"]} {name}',file=sys.stderr,flush=True)
                    start=time.perf_counter()
                    outcome=await review_reply(provider,case['candidate'],history,evidence,timeout=8)
                    elapsed=time.perf_counter()-start
                rows.append({'repeat':repetition+1,'variant':name,'id':case['id'],
                    'query':case['query'],'candidate':case['candidate'],'expected':case['expected'],
                    'status':outcome.status,'failure':outcome.failure,'match':outcome.status==case['expected'],
                    'elapsed_seconds':round(elapsed,3),'usage':usage,'http_status':http_status,
                    'review':outcome.result.model_dump() if outcome.result else None})
                print(f'result {name} {outcome.status} {outcome.failure} {elapsed:.3f}s',file=sys.stderr,flush=True)
    return {'baseline':BASELINE,'model':settings.selected_model,'dataset_sha256':digest,
            'indexed_prompt_sha256':hashlib.sha256(INDEXED_PROMPT.encode()).hexdigest(),
            'fixtures_sha256':hashlib.sha256(json.dumps(fixtures,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
            'timeout_seconds':8,'max_attempts':len(fixtures)*repeats*2,'summary':summarize(rows),
            'results':rows,'limits':'Fixed synthetic development probes, not independent blind evaluation. No retries, generation or database. Usage covers received responses only; timeouts may still incur billing.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--repeats',type=int,choices=(1,2),default=2)
    args=parser.parse_args()
    if not args.live:parser.error('显式--live才允许读取本地配置，最多32次合成裁判请求')
    from app.config import Settings
    settings=Settings(semantic_review_timeout_seconds=8)
    if settings.chat_provider!='gemini' or not settings.configured:parser.error('需要本地Gemini配置')
    try:report=asyncio.run(compare(settings,repeats=args.repeats))
    except KeyboardInterrupt:
        print('对照已中止，不生成完整报告。',file=sys.stderr);return 130
    except Exception:
        print('对照未完成，不显示原始异常或本地配置。',file=sys.stderr);return 2
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(any(not r['match'] for r in report['results']))


if __name__=='__main__':raise SystemExit(main())
