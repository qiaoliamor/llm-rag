"""Explicit live Gemini scene/place paired evaluation on synthetic data only."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.config import Settings
from app.dialogue import ProviderFailure,build_provider,instructions
from app.grounding import grounding_prompt,scene_conflicts,place_conflicts,protected_places
from app.memory import memory_prompt
from app.memory_source import source_time_conflicts
from scripts.evaluate_memory_source import CASES as SOURCE_CASES

# Two frozen source-time cases reproduce the previous failures; a third
# development probe asks directly about scene details. Not an independent holdout.
CASES = [next(c.copy() for c in SOURCE_CASES if c['id']==name) for name in ('pet','when')] + [
    {'id':'shop','fact':None,'event_date':None,
     'query':'你店里今天安静吗？是不是刚收到新书？',
     'expected':'不确认未知的店内近况或新书，不把问句预设当证据'}]


def evidence_for(case):
    return [] if case['fact'] is None else [{'id':'synthetic-'+case['id'],
                                           'fact':case['fact'],'event_date':case['event_date']}]


def prompt_for(case,after):
    evidence=evidence_for(case)
    base=instructions()+memory_prompt(evidence)
    return base+grounding_prompt(evidence,case['query']) if after else base


async def run(repeats=1,interval=12):
    if repeats not in (1,2) or not 0 <= interval <= 60: raise ValueError('invalid bounds')
    settings=Settings()
    if settings.chat_provider!='gemini' or not settings.configured: raise ValueError('requires Gemini')
    provider=build_provider(settings)
    trials=[]
    for index,case in enumerate(CASES):
        history=[{'role':'user','content':case['query']}]
        names=protected_places(evidence_for(case),case['query'])
        for repeat in range(repeats):
            order=[False,True] if (index+repeat)%2==0 else [True,False]
            for after in order:
                if trials and interval: await asyncio.sleep(interval)
                prompt=prompt_for(case,after)
                row={'id':case['id'],'repeat':repeat,'variant':'after' if after else 'before',
                     'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
                started=time.perf_counter()
                try:
                    reply=await provider.generate(history,prompt)
                    if not isinstance(reply,str) or not reply.strip(): raise ProviderFailure('empty_response','empty')
                    row.update(status='ok',reply=reply,scene_guard=scene_conflicts(reply),
                               place_guard=place_conflicts(reply,names),
                               source_time_guard=source_time_conflicts(reply,history))
                except ProviderFailure as exc:
                    row.update(status='error',code=exc.code)
                row['elapsed_ms']=(time.perf_counter()-started)*1000
                trials.append(row)
    return {'version':'scene-place-v1.1','provider':'gemini','model':settings.selected_model,
            'cases':CASES,'api_calls':len(trials),'trials':trials,'repeats':repeats,'interval_seconds':interval,
            'sampling':'provider defaults; max_tokens=500; counterbalanced; no retries or model judge',
            'limits':'Raw prompt-only outputs, no live rewrite. Guards are finite probes, not fact support labels. Author reviews every assertion; no blind assessment.',
            'token_usage':None,'actual_cost':None}


def run_pipeline():
    """One real /v1/chat request in disposable storage; at most two generations."""
    import tempfile
    from fastapi.testclient import TestClient
    from pydantic import SecretStr
    settings=Settings()
    if settings.chat_provider!='gemini' or not settings.configured: raise ValueError('requires Gemini')
    provider=build_provider(settings)
    requests=[]
    class RecordingProvider:
        async def generate(self,history,prompt):
            if len(requests)>=2: raise ValueError('generation budget exceeded')
            row={'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
            requests.append(row)
            try:
                reply=await provider.generate(history,prompt)
                row.update(status='ok',reply=reply)
                return reply
            except ProviderFailure as exc:
                row.update(status='error',code=exc.code)
                raise
    # app.main has a module-level app. Override its storage BEFORE importing it,
    # otherwise even a disposable test could initialize the real local database.
    import os
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix='persona-grounding-live-') as directory:
        url='sqlite:///'+directory+'/synthetic.db'
        with patch.dict(os.environ,{'MEMORY_DATABASE_URL':url}):
            from app.main import create_app,app as bootstrap_app
            local=settings.model_copy(update={'memory_database_url':SecretStr(url)})
            app=create_app(local,RecordingProvider())
            try:
                with TestClient(app) as client:
                    headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
                    response=client.post('/v1/chat',headers=headers,json={'message':CASES[-1]['query']})
                    data=response.json()
                    return {'version':'scene-place-v1.1-pipeline','model':settings.selected_model,
                            'case':CASES[-1],'status_code':response.status_code,'reply':data.get('reply'),
                            'guarded':data.get('guarded'),'code':data.get('code'),
                            'api_calls':len(requests)+data.get('semantic_review',{}).get('calls',0),
                            'generation_calls':len(requests),'semantic_review':data.get('semantic_review'),
                            'memory_route':data.get('memory_route'),'requests':requests}
            finally:
                app.state.memory_store.engine.dispose()
                if str(bootstrap_app.state.memory_store.engine.url)==url:
                    bootstrap_app.state.memory_store.engine.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pipeline',action='store_true',help='One synthetic /v1/chat with disposable database, at most two model calls')
    parser.add_argument('--repeats',type=int,choices=(1,2),default=1)
    parser.add_argument('--interval',type=float,default=12)
    args=parser.parse_args()
    try: report=run_pipeline() if args.pipeline else asyncio.run(run(args.repeats,args.interval))
    except Exception:
        print('对照未完成；请检查本地配置或网络，不显示原始配置或异常。',file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    failed=report['status_code']!=200 if args.pipeline else any(t['status']!='ok' for t in report['trials'])
    raise SystemExit(int(failed))
