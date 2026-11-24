"""Practical companion defaults, synthetic isolated stores and scripted providers."""
import asyncio
import json
import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
from app.config import Settings
from app.companion import relationship_context
from app.reply_pipeline import generate_checked
from app.dialogue import ProviderFailure
from scripts import smoke_companion as smoke


@pytest.mark.parametrize('locale',['zh-CN','ja-JP'])
@pytest.mark.parametrize('judge_available',[True,False])
def test_plain_chat_one_generation_even_if_judge_unavailable(locale,judge_available):
    generator=SimpleNamespace(generate=AsyncMock(return_value='普通の会話。'))
    judge=SimpleNamespace(review=AsyncMock(side_effect=TimeoutError())) if judge_available else None
    reply,guarded,status=asyncio.run(generate_checked(generator,[{'role':'user','content':'synthetic'}],'prompt','synthetic',[],None,
        {'status':'disabled','assessment':None},{'enabled':False},judge=judge,companion=True,multilingual_facts=True,
        locale=locale,review_policy='contextual'))
    assert reply=='普通の会話。' and not guarded and status=={'status':'prompt_only','calls':0}
    generator.generate.assert_awaited_once()
    if judge:judge.review.assert_not_awaited()


@pytest.mark.parametrize('trigger',['memory','empty_requested','weather','emotion','full','audit'])
def test_capability_context_and_full_mode_still_require_review(trigger):
    generator=SimpleNamespace(generate=AsyncMock(return_value='unreviewed synthetic'))
    judge=SimpleNamespace(review=AsyncMock(side_effect=TimeoutError()))
    kwargs={'companion':True,'multilingual_facts':True,'review_policy':'contextual'}
    if trigger=='full':kwargs['review_policy']='full'
    if trigger=='audit':kwargs['companion']=False
    if trigger=='empty_requested':kwargs['force_review']=True
    weather={'status':'ok','source':'mock','temperature_c':20} if trigger=='weather' else None
    mood={'status':'analyzed','assessment':{'source':'user','labels':['sadness'],'intensity':.5,'confidence':1,'response_strategy':'listen'}} if trigger=='emotion' else {'status':'disabled','assessment':None}
    kwargs.update(multilingual_weather=trigger=='weather',multilingual_emotion=trigger=='emotion')
    result=asyncio.run(generate_checked(generator,[],'prompt','synthetic',[{'id':'m','fact':'synthetic','event_date':None}] if trigger=='memory' else [],
        weather,mood,{'enabled':trigger=='emotion','preference':'listen'},judge=judge,**kwargs))
    assert result[0]!='unreviewed synthetic' and result[2]['calls']==1
    judge.review.assert_awaited_once();generator.generate.assert_awaited_once()


def test_contextual_default_and_invalid_setting(monkeypatch):
    monkeypatch.delenv('REPLY_REVIEW_POLICY',raising=False)
    assert Settings(_env_file=None).reply_review_policy=='contextual'
    with pytest.raises(ValidationError):Settings(_env_file=None,reply_review_policy='invalid')


@pytest.mark.parametrize('score,phrase',[(0,'刚认识'),(29,'刚认识'),(30,'已经熟悉'),(59,'已经熟悉'),(60,'相处亲近'),(89,'相处亲近'),(90,'男友般'),(100,'男友般')])
def test_closeness_prompt_follows_thresholds_without_granting_permissions(score,phrase):
    text=relationship_context(score)
    assert phrase in text and '独立授权' in text and '不证明已经恋爱' in text
    assert relationship_context(None)==''


def test_four_scripted_http_smoke_cases_one_call_each_and_correct_unlocks(monkeypatch):
    from app.dialogue import CHARACTER
    class Generator:
        async def generate(self,history,prompt):
            assert 'companion-closeness-v1' in prompt and CHARACTER['name'] in prompt
            assert '角色卡' in prompt
            return '合成会話の返事。'
    monkeypatch.setattr(smoke,'build_provider',lambda s:Generator())
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',growth_enabled=True,dialogue_mode='companion',
        reply_review_policy='contextual',reply_understanding_mode='semantic',memory_understanding_mode='semantic',
        weather_understanding_mode='semantic',emotion_understanding_mode='semantic')
    report=smoke.run(settings)
    assert report['attempted_calls']==report['max_calls']==4 and report['unattempted']==[]
    expected=[{'memory':False,'weather':False,'emotion':False},{'memory':True,'weather':False,'emotion':False},
        {'memory':True,'weather':True,'emotion':False},{'memory':True,'weather':True,'emotion':True}]
    for row,abilities in zip(report['results'],expected):
        assert row['technical_complete'] and row['saved_messages']==2 and row['abilities']==abilities
        assert row['review']=={'status':'prompt_only','calls':0}


def test_smoke_stops_after_first_generation_failure(monkeypatch):
    class Generator:
        async def generate(self,*a):raise ProviderFailure('timeout','synthetic failure',504)
    monkeypatch.setattr(smoke,'build_provider',lambda s:Generator())
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',growth_enabled=True,dialogue_mode='companion',reply_review_policy='contextual')
    report=smoke.run(settings)
    assert report['attempted_calls']==1 and len(report['unattempted'])==3
    assert report['results'][0]['http_status']==504 and report['results'][0]['saved_messages']==0


def test_smoke_without_live_never_reads_env_or_connects(tmp_path):
    (tmp_path/'sitecustomize.py').write_text('import sys,os\ndef guard(e,a):\n if e=="open" and isinstance(a[0],(str,bytes)) and os.fsdecode(a[0]).endswith("/.env"):raise RuntimeError("forbidden")\n if e=="socket.connect":raise RuntimeError("forbidden")\nsys.addaudithook(guard)\n')
    result=subprocess.run([sys.executable,'scripts/smoke_companion.py'],capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(tmp_path)})
    assert result.returncode==2 and '--live required' in result.stderr


@pytest.mark.parametrize('case',[smoke.CASES[0],smoke.CASES[-1]])
def test_contextual_chat_in_disposable_postgres_only(case):
    url=os.environ.get('TEST_POSTGRES_URL')
    if not url:pytest.skip('script-created temporary PG only')
    class Generator:
        async def generate(self,history,prompt):return '合成の返答。'
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',growth_enabled=True,dialogue_mode='companion',
        reply_review_policy='contextual',reply_understanding_mode='semantic',memory_understanding_mode='semantic',
        weather_understanding_mode='semantic',emotion_understanding_mode='semantic')
    result=smoke.run_case(settings,Generator(),case,url)
    assert result['technical_complete'] and result['saved_messages']==2
    assert result['abilities']=={'memory':case['score']>=30,'weather':case['score']>=60,'emotion':case['score']>=90}


def test_consent_epoch_change_still_invalidates_prompt_only_reply(tmp_path):
    from app.main import create_app
    from fastapi.testclient import TestClient
    app=None;uid=None
    class Generator:
        async def generate(self,history,prompt):
            app.state.memory_store.configure(uid,False,'Asia/Tokyo')
            return 'must not be saved'
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',growth_enabled=True,dialogue_mode='companion',
        reply_review_policy='contextual',reply_understanding_mode='semantic',memory_understanding_mode='semantic',
        memory_database_url='sqlite:///'+str(tmp_path/'synthetic.sqlite3'))
    app=create_app(settings,provider=Generator())
    try:
        with TestClient(app) as c:
            session=c.get('/v1/session').json();uid=next(iter(app.state.sessions.values())).user_id
            app.state.memory_store.configure(uid,True,'Asia/Tokyo')
            result=c.post('/v1/chat',headers={'x-csrf-token':session['csrf_token']},json={'message':'合成挨拶'})
            assert result.status_code==409 and result.json()['code']=='memory_changed'
            assert c.get('/v1/session').json()['messages']==[]
    finally:app.state.memory_store.engine.dispose()
