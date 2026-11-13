"""Default semantic fact path with synthetic players and disposable stores."""
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.progression import Bond
from app.memory_understanding import MemoryMetadata
from app import fact_presentation as f
from test_fact_presentation import judgment


def plan(need=False):
    return {'memory_use':'allow','need_memory':need,'query':'合成桜ヶ丘市 住址' if need else '',
        'target_slots':['residence'] if need else [],'reason':'personal_history_needed' if need else 'no_cross_session_need',
        'confidence':.95,'candidates':[]}


@pytest.fixture(params=['sqlite','postgres'])
def env(request,tmp_path):
    url=os.environ.get('TEST_POSTGRES_URL') if request.param=='postgres' else 'sqlite:///'+str(tmp_path/'facts.sqlite3')
    if not url:pytest.skip('requires independent temporary PostgreSQL')
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',dialogue_mode='companion',growth_enabled=True,
        reply_understanding_mode='semantic',memory_understanding_mode='semantic',weather_understanding_mode='semantic',
        emotion_understanding_mode='semantic',memory_database_url=url)
    provider=SimpleNamespace(generate=AsyncMock(return_value='うん、聞いているよ。'))
    judge=SimpleNamespace(review=AsyncMock(side_effect=lambda text,history,evidence:judgment(text)))
    analyst=SimpleNamespace(analyze=AsyncMock(return_value=plan()),select=AsyncMock(return_value={'ids':[],'confidence':.95}))
    app=create_app(settings,provider,semantic_judge=judge,memory_understander=analyst)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    uid=next(iter(app.state.sessions.values())).user_id
    return SimpleNamespace(settings=settings,provider=provider,judge=judge,analyst=analyst,app=app,c=c,h=h,uid=uid,store=app.state.memory_store)


def chat(x,text='こんにちは',locale='ja-JP'):
    return x.c.post('/v1/chat',headers=x.h,json={'message':text,'locale':locale})


def enable_memory(x):
    with x.store.db.begin() as db:db.get(Bond,(x.uid,'shen_yan')).score=30
    assert x.c.patch('/v1/settings',headers=x.h,json={'memory_enabled':True,'timezone':'Asia/Tokyo'}).status_code==200


@pytest.mark.parametrize('locale,text',[('ja-JP','こんにちは'),('zh-CN','你好')])
def test_greeting_with_locked_abilities_has_one_shared_review_no_semantic_admission_call(env,locale,text):
    x=env;x.provider.generate.return_value=text+' 話したいことからどうぞ。' if locale=='ja-JP' else text+'，今天想聊些什么？'
    r=chat(x,text,locale)
    assert r.status_code==200 and r.json()['reply']==x.provider.generate.return_value and r.json()['semantic_review']['calls']==1
    x.judge.review.assert_awaited_once();x.provider.generate.assert_awaited_once();x.analyst.analyze.assert_not_awaited()
    assert f.ANSWER_PROMPT in x.provider.generate.call_args.args[1]
    policy=next(e['data'] for e in x.judge.review.call_args.args[2] if e['id']=='reply_policy')
    assert policy=={'reply_locale':locale}


@pytest.mark.parametrize('locale',['ja-JP','zh-CN'])
def test_current_canon_reply_cites_frozen_evidence_and_rewrites_one_time(env,locale):
    x=env;bad='僕は30歳の医師だよ。';good='28歳で、栖川の古書店を営んでいるよ。'
    x.provider.generate.side_effect=[bad,good]
    x.judge.review.side_effect=[judgment(bad,'contradicted'),judgment(good,'supported',['C01','C02'])]
    r=chat(x,'職業と年齢は？',locale)
    assert r.status_code==200 and r.json()['reply']==good and r.json()['guarded']
    assert r.json()['semantic_review']['calls']==2
    evidence=x.judge.review.call_args.args[2]
    assert next(e['text'] for e in evidence if e['id']=='C01')=='沈砚今年28岁。'
    assert x.c.get('/v1/session').json()['messages'][-1]['content']==good


@pytest.mark.parametrize('failure',['timeout','invalid','foreign_id'])
def test_review_failure_preserves_state_and_failure_reporting(env,failure):
    x=env;x.provider.generate.return_value='話したいことから聞かせて。'
    if failure=='timeout':x.judge.review.side_effect=TimeoutError()
    else:x.judge.review.side_effect=None;x.judge.review.return_value={'bad':'synthetic'} if failure=='invalid' else judgment(x.provider.generate.return_value,'supported',['foreign'])
    r=chat(x)
    if failure=='timeout':
        assert r.status_code==503 and x.c.get('/v1/session').json()['messages']==[]
    else:
        assert r.status_code==200 and r.json()['guarded'] and r.json()['reply'].startswith('うん')
        assert r.json()['semantic_review']['status']=='unavailable'
    assert x.c.get('/v1/memories').json()['items']==[]
    x.provider.generate.assert_awaited_once();x.judge.review.assert_awaited_once()


def test_no_judge_is_localized_natural_bounded_fallback(env):
    x=env;x.provider.generate.return_value='僕は30歳だよ。'
    app=create_app(x.settings,x.provider,memory_understander=x.analyst)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    r=c.post('/v1/chat',headers=h,json={'message':'年齢は？','locale':'ja-JP'})
    assert r.status_code==200 and r.json()['semantic_review']['status']=='reply_safe_fallback'
    assert r.json()['reply'].startswith('うん')


def test_revoke_during_fact_review_invalidates_turn(env):
    x=env;enable_memory(x);x.provider.generate.return_value='話したいことから聞かせて。'
    async def revoke(reply,history,evidence):
        x.store.configure(x.uid,False,'Asia/Tokyo')
        return judgment(reply)
    x.judge.review.side_effect=revoke
    assert chat(x).status_code==409
    assert x.c.get('/v1/session').json()['messages']==[]
    assert x.c.get('/v1/memories').json()['items']==[]


def test_configured_factory_selects_fact_provider_and_preserves_legacy_choice(env,monkeypatch):
    x=env;x.provider.generate.return_value='話したいことから聞かせて。';factory=Mock(return_value=x.judge)
    monkeypatch.setattr('app.fact_presentation.FactAnalysisProvider',factory)
    settings=x.settings.model_copy(update={'chat_provider':'gemini'})
    app=create_app(settings,x.provider,memory_understander=x.analyst)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    assert c.post('/v1/chat',headers=h,json={'message':'こんにちは','locale':'ja-JP'}).status_code==200
    factory.assert_called_once_with(settings)
    legacy=Mock(return_value=x.judge);monkeypatch.setattr('app.emotion_presentation.EmotionAnalysisProvider',legacy)
    create_app(settings.model_copy(update={'reply_understanding_mode':'legacy'}),x.provider,memory_understander=x.analyst)
    legacy.assert_called_once()


def test_confirmed_memory_cross_session_source_time_correction_delete_and_no_revival(env):
    x=env;enable_memory(x)
    # Manual metadata failure keeps exact original and unknown date; it cannot confirm.
    path='/v1/memories'
    fact='合成桜ヶ丘市に住んでいます。'
    r=x.c.post(path,headers=x.h,json={'fact':fact})
    assert r.status_code==200
    m=r.json()['item'];assert m['status']=='candidate'
    x.analyst.analyze.return_value=plan(True)
    assert chat(x,'住んでいる場所を覚えてる？').json()['retrieved_memory_ids']==[]
    m=x.c.patch(path+'/'+m['id'],headers=x.h,json={'version':m['version'],'confirm':True}).json()['item']
    # Use a broad query: default metadata is other, not a guessed residence classification.
    x.analyst.analyze.return_value={**plan(True),'target_slots':[],'query':fact}
    x.analyst.select.return_value={'ids':[m['id']],'confidence':.95}
    app=create_app(x.settings,x.provider,semantic_judge=x.judge,memory_understander=x.analyst)
    c=TestClient(app);c.cookies.update(x.c.cookies);x.app=app;x.c=c;x.h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    bad='さっき合成桜ヶ丘市に住んでいると教えてくれたね。';good='合成桜ヶ丘市に住んでいることは覚えているよ。'
    x.provider.generate.side_effect=[bad,good]
    x.judge.review.side_effect=[judgment(bad,'unsupported'),judgment(good,'supported',['memory_'+m['id']])]
    result=chat(x,'住んでいる場所を覚えてる？').json()
    assert result['reply']==good and result['retrieved_memory_ids']==[m['id']]
    assert '本轮需保留完整写法' not in x.provider.generate.call_args.args[1]
    evidence=x.judge.review.call_args.args[2]
    assert next(e for e in evidence if e['id']=='memory_'+m['id'])['event_date'] is None
    # Ownership, CSRF, optimistic version are checked before metadata inference.
    other=TestClient(app);oh={'x-csrf-token':other.get('/v1/session').json()['csrf_token']}
    assert other.patch(path+'/'+m['id'],headers=oh,json={'version':m['version'],'fact':'合成別町に住んでいます。'}).status_code==404
    assert x.c.patch(path+'/'+m['id'],headers={'x-csrf-token':'invalid'},json={'version':m['version'],'fact':'合成別町に住んでいます。'}).status_code==403
    assert x.c.patch(path+'/'+m['id'],headers=x.h,json={'version':m['version']-1,'fact':'合成別町に住んでいます。'}).status_code==409
    newfact='合成別町に住んでいます。'
    edited=x.c.patch(path+'/'+m['id'],headers=x.h,json={'version':m['version'],'fact':newfact})
    assert edited.status_code==200
    m=edited.json()['item'];assert m['fact']==newfact and m['version']>1
    assert x.c.get('/v1/session').json()['messages']==[]
    assert x.c.delete(path+'/'+m['id'],headers=x.h,params={'version':m['version']}).status_code==200
    assert x.c.get(path).json()['items']==[]
    assert not x.store.semantic_candidates(x.uid,newfact)
    x.provider.generate.side_effect=None;x.judge.review.side_effect=lambda text,history,evidence:judgment(text)
    x.analyst.select.return_value={'ids':[],'confidence':.95}
    r=chat(x,'住んでいる場所を覚えてる？')
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[]
    assert not any(e['id'].startswith('memory_') for e in x.judge.review.call_args.args[2])
    # Reopening uses the same synthetic identity; deleted vector/text remain absent.
    new=TestClient(create_app(x.settings,x.provider,semantic_judge=x.judge,memory_understander=x.analyst));new.cookies.update(x.c.cookies)
    new.get('/v1/session')
    assert new.get(path).json()['items']==[]


def test_actual_unconfigured_defaults_choose_semantic_reply_and_reject_invalid_locale_before_generation(env,monkeypatch):
    x=env;x.provider.generate.return_value='話したいことから聞かせて。'
    for key in ('REPLY_UNDERSTANDING_MODE','MEMORY_UNDERSTANDING_MODE','WEATHER_UNDERSTANDING_MODE','EMOTION_UNDERSTANDING_MODE','DIALOGUE_MODE','GROWTH_ENABLED'):
        monkeypatch.delenv(key,raising=False)
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',memory_database_url=x.settings.memory_database_url)
    assert settings.reply_understanding_mode==settings.memory_understanding_mode==settings.weather_understanding_mode==settings.emotion_understanding_mode=='semantic'
    assert settings.dialogue_mode=='companion' and settings.growth_enabled
    app=create_app(settings,x.provider,semantic_judge=x.judge,memory_understander=x.analyst)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    assert c.post('/v1/chat',headers=h,json={'message':'こんにちは','locale':'invalid'}).status_code==422
    x.provider.generate.assert_not_awaited();x.judge.review.assert_not_awaited()
    r=c.post('/v1/chat',headers=h,json={'message':'こんにちは','locale':'ja-JP'})
    assert r.status_code==200 and r.json()['semantic_review']['status']=='accepted'
    assert r.json()['semantic_review']['calls']==1


@pytest.mark.parametrize('mode',['companion','audit'])
def test_semantic_main_does_not_run_legacy_place_extraction_in_either_dialogue_mode(env,monkeypatch,mode):
    x=env
    def forbidden(*a,**kw):raise AssertionError('legacy place extraction invoked')
    monkeypatch.setattr('app.main.grounding_prompt',forbidden)
    monkeypatch.setattr('app.companion.protected_places',forbidden)
    settings=x.settings.model_copy(update={'dialogue_mode':mode})
    app=create_app(settings,x.provider,semantic_judge=x.judge,memory_understander=x.analyst)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    r=c.post('/v1/chat',headers=h,json={'message':'合成の会話','locale':'ja-JP'})
    assert r.status_code==200 and f.ANSWER_PROMPT in x.provider.generate.call_args.args[1]
