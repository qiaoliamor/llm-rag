"""Four fixed synthetic usability cases, one Gemini generation each, no retries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
from pydantic import SecretStr
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.config import ROOT,Settings
from app.dialogue import build_provider,ProviderFailure

CASES=(
    {'id':'zh-greeting','locale':'zh-CN','score':0,'message':'你好，今天第一次来找你聊天。'},
    {'id':'ja-casual','locale':'ja-JP','score':30,'message':'今日は特に何もなかったけど、少し話したくなった。'},
    {'id':'zh-character','locale':'zh-CN','score':60,'message':'你多大啦？平时做什么，这家书店是怎么开起来的？'},
    {'id':'ja-care','locale':'ja-JP','score':90,'message':'今日はちょっと疲れた。アドバイスより、恋人みたいに優しく話しかけてほしい。'},
)


class NoAuxiliary:
    async def analyze(self,*a,**kw):raise ProviderFailure('test_call_budget','No auxiliary calls in ordinary-chat smoke.',503)
    async def select(self,*a,**kw):raise ProviderFailure('test_call_budget','No selection in ordinary-chat smoke.',503)
    async def review(self,*a,**kw):raise ProviderFailure('test_call_budget','No judge in ordinary-chat smoke.',503)
    async def assess(self,*a,**kw):raise ProviderFailure('test_call_budget','No emotion API in ordinary-chat smoke.',503)


def run_case(settings,provider,case,url):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.progression import Bond
    app=create_app(settings.model_copy(update={'memory_database_url':SecretStr(url)}),provider=provider,
        memory_understander=NoAuxiliary(),weather_understander=NoAuxiliary(),emotion_understander=NoAuxiliary(),semantic_judge=NoAuxiliary())
    store=app.state.memory_store
    try:
        with TestClient(app) as client:
            session=client.get('/v1/session').json();headers={'x-csrf-token':session['csrf_token']}
            uid=next(iter(app.state.sessions.values())).user_id
            with store.db.begin() as db:db.get(Bond,(uid,'shen_yan')).score=case['score']
            start=time.monotonic()
            result=client.post('/v1/chat',headers=headers,json={'message':case['message'],'locale':case['locale']})
            elapsed=round(time.monotonic()-start,3);body=result.json()
            saved=client.get('/v1/session').json();account=client.get('/v1/account').json()
            return {'case':case,'http_status':result.status_code,'elapsed_seconds':elapsed,'reply':body.get('reply'),
                'failure':body.get('code'),'review':body.get('semantic_review'),'saved_messages':len(saved['messages']),
                'abilities':account['character']['abilities'],'score_after':account['character']['score'],
                'technical_complete':bool(result.status_code==200 and body.get('reply') and body.get('semantic_review',{}).get('status')=='prompt_only')}
    finally:store.engine.dispose()


def run(settings):
    provider=build_provider(settings);calls=[];rows=[]
    class Generator:
        async def generate(self,history,prompt):
            if len(calls)>=4:raise ProviderFailure('test_call_budget','No extra request.',503)
            item={'stage':'generation','status':'started'};calls.append(item);start=time.monotonic()
            try:
                text=await provider.generate(history,prompt);item['status']='returned';return text
            except BaseException:
                item['status']='failed';raise
            finally:item['elapsed_seconds']=round(time.monotonic()-start,3)
    with tempfile.TemporaryDirectory(prefix='practical-companion-') as scratch:
        for i,case in enumerate(CASES):
            with patch.dict(Settings.model_config,env_file=None),patch.dict(os.environ,CHAT_PROVIDER='mock',WEATHER_PROVIDER='mock',
                    GEMINI_API_KEY='',OPENAI_API_KEY='',MEMORY_DATABASE_URL='sqlite:///'+str(Path(scratch)/'bootstrap.sqlite3')):
                row=run_case(settings,Generator(),case,'sqlite:///'+str(Path(scratch)/f'case-{i}.sqlite3'))
            rows.append(row)
            if not row['technical_complete']:break
    paths=('app/config.py','app/companion.py','app/main.py','app/reply_pipeline.py','app/localization.py','characters/shen_yan.json','scripts/smoke_companion.py')
    return {'mode':'practical_companion_smoke','model':settings.selected_model,'review_policy':settings.reply_review_policy,
        'max_calls':4,'attempted_calls':len(calls),'calls':calls,'results':rows,'unattempted':[c['id'] for c in CASES[len(rows):]],
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        'limits':'Synthetic ordinary chat only; permissions off, no memory/weather/emotion API, no retry. Developer usability observations, not independent quality or hallucination benchmark. No M6 acceptance.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true');args=parser.parse_args()
    if not args.live:parser.error('--live required; at most 4 generations, stop on error, no retry')
    from dotenv import dotenv_values
    values=dotenv_values(ROOT/'.env');key=os.environ.get('GEMINI_API_KEY') or values.get('GEMINI_API_KEY','')
    if not key:parser.error('Local key required; omitted')
    model=os.environ.get('GEMINI_MODEL') or values.get('GEMINI_MODEL') or Settings.model_fields['gemini_model'].default
    settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key=key,gemini_model=model,weather_provider='mock',
        dialogue_mode='companion',growth_enabled=True,reply_review_policy='contextual',memory_understanding_mode='semantic',
        weather_understanding_mode='semantic',emotion_understanding_mode='semantic',reply_understanding_mode='semantic')
    try:report=run(settings)
    except Exception:
        print('Synthetic smoke incomplete; private exception/configuration omitted.',file=sys.stderr);return 2
    encoded=json.dumps(report,ensure_ascii=False,indent=2)
    if key in encoded:raise SystemExit('Sensitive output blocked')
    print(encoded);return int(bool(report['unattempted']) or any(not row['technical_complete'] for row in report['results']))


if __name__=='__main__':raise SystemExit(main())
