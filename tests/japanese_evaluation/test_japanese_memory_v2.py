"""Japanese v2 SDK and default-path contracts; all interpretations are scripted."""
import asyncio
from datetime import datetime, timezone
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.progression import Bond
from app.localization import JAPANESE_PROMPT, JAPANESE_PROMPT_V1, JAPANESE_STYLE_VERSION
from app.memory_understanding import (ModelMemoryUnderstanding, MemoryPlan, PLAN_PROMPT, PLAN_PROMPT_V1,
    POLICY_VERSION, understand)


def plan(candidates=(),**kw):
    return {'memory_use':'allow','need_memory':False,'query':'','target_slots':[],'reason':'no_cross_session_need',
        'confidence':.95,'candidates':list(candidates),**kw}


def proposal(text,subject='user',actuality='asserted',slot='appointment',date=None):
    return {'source_text':text,'subject':subject,'actuality':actuality,'category':'event' if slot=='appointment' else 'preference',
        'slot':slot,'confidence':.95,'date':date or {'kind':'unknown','expression':'','absolute':None,'days':None,'week_offset':None,'weekday':None}}


def accepted(text,history,evidence):
    return {'decision':'accept','confidence':.95,'role_issues':[],
        'segments':[{'text':text,'kind':'nonfactual','verdict':'not_applicable','evidence_ids':[],'reason':'nonfactual'}]}


def test_real_sdk_payload_preserves_v1_and_adds_japanese_v2_without_live_calls():
    calls=[]
    def handler(request):
        body=json.loads(request.content);calls.append(body)
        assert body['messages'][0]['content']==PLAN_PROMPT and PLAN_PROMPT.startswith(PLAN_PROMPT_V1)
        result=plan()
        return httpx.Response(200,json={'id':'synthetic','object':'chat.completion','created':0,'model':'synthetic',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(result)}}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            p=ModelMemoryUnderstanding(Settings(_env_file=None,chat_provider='gemini',gemini_api_key='synthetic-not-a-key'),client)
            return await p.analyze({'current_message':'こんばんは','recent_dialogue':[],'today':'2026-11-13','timezone':'Asia/Tokyo','operation':'chat'})
    assert isinstance(asyncio.run(run()),MemoryPlan) and len(calls)==1
    assert JAPANESE_PROMPT.startswith(JAPANESE_PROMPT_V1) and JAPANESE_STYLE_VERSION in JAPANESE_PROMPT
    assert POLICY_VERSION=='multilingual-memory-ja-v2'


@pytest.mark.parametrize('text,subject,actuality,accepted_count',[
    ('明日、面接なんだ。','user','asserted',1),
    ('妹は明日、面接なんだ。','other','asserted',0),
    ('「明日、面接なんだ」と友だちが言った。','other','quoted',0),
    ('もし明日面接だったら。','user','hypothetical',0),
])
def test_ellipsis_other_quote_hypothetical_protocol_never_confirms_on_its_own(text,subject,actuality,accepted_count):
    analyst=SimpleNamespace(analyze=AsyncMock(return_value=plan([proposal(text,subject,actuality)])))
    result=asyncio.run(understand(analyst,text,[],enabled=True,tz='Asia/Tokyo',now=datetime(2026,11,13,tzinfo=timezone.utc)))
    assert result.status=='ready' and len(result.candidates)==accepted_count
    if result.candidates:assert result.candidates[0].fact==text and result.candidates[0].metadata.event_date is None


@pytest.fixture(params=['sqlite','postgres'])
def env(request,tmp_path,monkeypatch):
    url=os.environ.get('TEST_POSTGRES_URL') if request.param=='postgres' else 'sqlite:///'+str(tmp_path/'ja-v2.sqlite3')
    if not url:pytest.skip('requires independent temporary PostgreSQL')
    monkeypatch.setattr('app.memory_understanding.local_now',lambda tz:datetime(2026,11,13,tzinfo=timezone.utc))
    analyst=SimpleNamespace(analyze=AsyncMock(return_value=plan()),select=AsyncMock(return_value={'ids':[],'confidence':.95}))
    provider=SimpleNamespace(generate=AsyncMock(return_value='うん。その話、聞かせて。'))
    judge=SimpleNamespace(review=AsyncMock(side_effect=accepted))
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',reply_understanding_mode='semantic',
        memory_understanding_mode='semantic',weather_understanding_mode='semantic',emotion_understanding_mode='semantic',
        dialogue_mode='companion',growth_enabled=True,memory_database_url=url)
    app=create_app(settings,provider,memory_understander=analyst,semantic_judge=judge)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    uid=next(iter(app.state.sessions.values())).user_id
    with app.state.memory_store.db.begin() as db:db.get(Bond,(uid,'shen_yan')).score=30
    assert c.patch('/v1/settings',headers=h,json={'memory_enabled':True,'timezone':'Asia/Tokyo'}).status_code==200
    return SimpleNamespace(c=c,h=h,app=app,uid=uid,store=app.state.memory_store,analyst=analyst,provider=provider,judge=judge,settings=settings)


def test_japanese_v2_original_date_confirmation_retrieval_correction_delete_and_chinese_switch(env):
    x=env;text='来週の火曜、合成青梧社の面接なんだ。'
    date={'kind':'weekday','expression':'来週の火曜','absolute':None,'days':None,'week_offset':1,'weekday':1}
    x.analyst.analyze.return_value=plan([proposal(text,date=date)])
    r=x.c.post('/v1/chat',headers=x.h,json={'message':text,'locale':'ja-JP'})
    assert r.status_code==200
    m=r.json()['memory_candidates'][0]
    assert m['fact']==text and m['event_date']=='2026-11-17' and m['status']=='candidate'
    assert JAPANESE_PROMPT in x.provider.generate.call_args.args[1]
    assert r.json()['retrieved_memory_ids']==[]
    m=x.c.patch('/v1/memories/'+m['id'],headers=x.h,json={'version':m['version'],'confirm':True}).json()['item']
    x.analyst.analyze.return_value=plan(need_memory=True,query='合成青梧社 面接',target_slots=['appointment'],reason='personal_history_needed')
    x.analyst.select.return_value={'ids':[m['id']],'confidence':.95}
    x.c.delete('/v1/session',headers=x.h)
    r=x.c.post('/v1/chat',headers=x.h,json={'message':'选考安排还记得吗？','locale':'zh-CN'})
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[m['id']]
    prompt=x.provider.generate.call_args.args[1]
    assert JAPANESE_PROMPT not in prompt and text in prompt and '2026-11-17' in prompt
    # Editing uses a new source and does not turn unknown date into old parsed date.
    revised='合成青梧社の面接は来月に変わった。'
    x.analyst.analyze.return_value=plan([proposal(revised)])
    m=x.c.patch('/v1/memories/'+m['id'],headers=x.h,json={'version':m['version'],'fact':revised}).json()['item']
    assert m['fact']==revised and m['event_date'] is None
    assert x.c.delete('/v1/memories/'+m['id'],headers=x.h,params={'version':m['version']}).status_code==200
    assert x.c.get('/v1/memories').json()['items']==[]
    assert x.store.semantic_candidates(x.uid,'面接',target_slots=['appointment'])==[]


def test_v2_refusal_and_authorization_revoke_prevent_memory_access(env):
    x=env
    x.analyst.analyze.return_value=plan(memory_use='decline',reason='declined')
    assert x.c.post('/v1/chat',headers=x.h,json={'message':'昔のことは調べないで','locale':'ja-JP'}).json()['retrieved_memory_ids']==[]
    x.analyst.select.assert_not_awaited()
    assert x.c.patch('/v1/settings',headers=x.h,json={'memory_enabled':False,'timezone':'Asia/Tokyo'}).status_code==200
    x.analyst.analyze.reset_mock()
    assert x.c.post('/v1/chat',headers=x.h,json={'message':'面接のこと覚えてる？','locale':'ja-JP'}).status_code==200
    x.analyst.analyze.assert_not_awaited()
