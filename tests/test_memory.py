import asyncio
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from app.config import Settings
from app.main import create_app
from app.memory import Memory, MemoryStore, describe, extract_candidates, memory_prompt, embed, EMBEDDING_VERSION


@pytest.fixture(params=['sqlite', 'postgres'])
def database_url(request, tmp_path):
    if request.param == 'postgres':
        url = os.environ.get('TEST_POSTGRES_URL')
        if not url: pytest.skip('Set TEST_POSTGRES_URL for PostgreSQL/pgvector integration')
        return url
    return 'sqlite:///' + str(tmp_path / 'memory.sqlite3')


def app_for(url, provider=None):
    return create_app(Settings(_env_file=None, chat_provider='mock', memory_database_url=url), provider)


def boot(app):
    client=TestClient(app)
    session=client.get('/v1/session').json()
    return client, {'x-csrf-token':session['csrf_token']}


def enable(client, headers, enabled=True):
    r=client.patch('/v1/settings',headers=headers,json={'memory_enabled':enabled,'timezone':'Asia/Tokyo'})
    assert r.status_code==200
    return r.json()['settings']


def manual(client, headers, fact, confirm=True, replace=False):
    r=client.post('/v1/memories',headers=headers,json={'fact':fact})
    assert r.status_code==200
    m=r.json()['item']
    if confirm:
        r=client.patch('/v1/memories/'+m['id'],headers=headers,json={'version':m['version'],'confirm':True,'replace_conflicts':replace})
        assert r.status_code==200
        m=r.json()['item']
    return m


def test_opt_in_candidates_and_confirmation(database_url):
    client,headers=boot(app_for(database_url))
    assert not client.get('/v1/memories').json()['settings']['memory_enabled']
    client.post('/v1/chat',headers=headers,json={'message':'我明天下午有面试'})
    assert client.get('/v1/memories').json()['items']==[]
    enable(client,headers)
    r=client.post('/v1/chat',headers=headers,json={'message':'我下周二有设计师面试'})
    assert r.status_code==200
    assert len(r.json()['memory_candidates'])==1
    m=r.json()['memory_candidates'][0]
    assert m['status']=='candidate' and m['source_message_id']
    assert m['event_date']
    client.delete('/v1/session',headers=headers)
    assert client.post('/v1/chat',headers=headers,json={'message':'还记得我的面试吗？'}).json()['retrieved_memory_ids']==[]
    r=client.patch('/v1/memories/'+m['id'],headers=headers,json={'version':m['version'],'confirm':True})
    assert r.status_code==200
    client.delete('/v1/session',headers=headers)
    answer=client.post('/v1/chat',headers=headers,json={'message':'你记得我的面试吗？'}).json()
    assert m['id'] in answer['retrieved_memory_ids']
    assert '设计师面试' in answer['reply']


def test_restart_and_browser_identity(database_url):
    app=app_for(database_url); client,headers=boot(app)
    enable(client,headers);m=manual(client,headers,'我喜欢在周末修补旧书')
    cookies=dict(client.cookies)
    restarted=TestClient(app_for(database_url));restarted.cookies.update(cookies)
    session=restarted.get('/v1/session').json()
    assert session['messages']==[]
    assert m['id'] in [i['id'] for i in restarted.get('/v1/memories').json()['items']]
    r=restarted.post('/v1/chat',headers={'x-csrf-token':session['csrf_token']},json={'message':'你记得我的爱好吗？'})
    assert m['id'] in r.json()['retrieved_memory_ids']
    other,_=boot(app)
    assert other.get('/v1/memories').json()['items']==[]


def test_owner_csrf_and_other_roles(database_url):
    app=app_for(database_url); a,ha=boot(app);b,hb=boot(app)
    enable(a,ha);enable(b,hb);m=manual(a,ha,'我叫合成测试甲')
    assert b.patch('/v1/memories/'+m['id'],headers=hb,json={'version':m['version'],'fact':'我叫乙'}).status_code==404
    assert b.delete('/v1/memories/'+m['id'],headers=hb,params={'version':m['version']}).status_code==404
    assert a.patch('/v1/settings',headers=hb,json={'memory_enabled':False}).status_code==403
    assert a.patch('/v1/settings',headers={**ha,'origin':'https://evil.example'},json={'memory_enabled':False}).status_code==403
    store=app.state.memory_store
    with store.db.begin() as db:
        stored=db.get(Memory,m['id']);stored.character_id='another_role'
    assert a.get('/v1/memories').json()['items']==[]
    uid=next(s.user_id for s in app.state.sessions.values() if store.is_owner(s.user_id,a.cookies.get('persona_player')))
    assert store.retrieve(uid,'你记得我的名字吗')==[]


def test_correction_versions_and_deletion(database_url):
    app=app_for(database_url);c,h=boot(app);enable(c,h);m=manual(c,h,'我叫旧名字合成甲')
    r=c.patch('/v1/memories/'+m['id'],headers=h,json={'version':m['version'],'fact':'我叫新名字合成乙'})
    assert r.status_code==200
    updated=r.json()['item']
    assert updated['version']==m['version']+1
    assert c.patch('/v1/memories/'+m['id'],headers=h,json={'version':m['version'],'fact':'过期修改'}).status_code==409
    r=c.post('/v1/chat',headers=h,json={'message':'我叫什么名字？'})
    assert '新名字合成乙' in r.json()['reply'] and '旧名字合成甲' not in r.json()['reply']
    assert c.delete('/v1/memories/'+m['id'],headers=h,params={'version':updated['version']}).status_code==200
    assert c.get('/v1/session').json()['messages']==[]
    r=c.post('/v1/chat',headers=h,json={'message':'我叫什么名字？'})
    assert r.json()['retrieved_memory_ids']==[]
    # Repeating the old message does not rebuild an auto candidate after deletion.
    r=c.post('/v1/chat',headers=h,json={'message':'我叫新名字合成乙'})
    assert r.json()['memory_candidates']==[]
    with app.state.memory_store.db() as db:
        assert db.get(Memory,m['id']) is None


def test_duplicate_conflicts_require_explicit_replacement(database_url):
    c,h=boot(app_for(database_url));enable(c,h)
    first=manual(c,h,'我住在合成城市甲')
    assert manual(c,h,'我住在合成城市甲',False)['id']==first['id']
    other=manual(c,h,'我住在合成城市乙',False)
    listed=c.get('/v1/memories').json()['items']
    assert first['id'] in next(m for m in listed if m['id']==other['id'])['conflicts']
    assert c.patch('/v1/memories/'+other['id'],headers=h,json={'version':other['version'],'confirm':True}).status_code==409
    assert c.patch('/v1/memories/'+other['id'],headers=h,json={'version':other['version'],'confirm':True,'replace_conflicts':True}).status_code==200
    items=c.get('/v1/memories').json()['items']
    assert len(items)==1 and items[0]['fact']=='我住在合成城市乙'


def test_disable_and_clear(database_url):
    c,h=boot(app_for(database_url));enable(c,h);manual(c,h,'我喜欢合成蓝色杯子');manual(c,h,'我叫待确认名字',False)
    enable(c,h,False)
    items=c.get('/v1/memories').json()['items']
    assert len(items)==1 and items[0]['status']=='confirmed'
    assert c.post('/v1/chat',headers=h,json={'message':'记得我的偏好吗'}).json()['retrieved_memory_ids']==[]
    assert c.post('/v1/memories',headers=h,json={'fact':'我叫测试'}).status_code==409
    assert c.delete('/v1/memories',headers=h).status_code==200
    assert c.get('/v1/memories').json()['items']==[]


def test_epoch_prevents_revoked_writes(database_url):
    store=MemoryStore(database_url);uid,_=store.identity(None)
    initial=store.configure(uid,True,'Asia/Tokyo')
    store.clear(uid)
    assert store.candidate(uid,'我明天有面试','source',initial['epoch']) is None
    fresh=store.settings(uid)
    store.configure(uid,False,'Asia/Tokyo')
    assert store.candidate(uid,'我叫测试','source',fresh['epoch']) is None


def test_expiry_retrieval_and_embedding_versions(database_url):
    app=app_for(database_url);c,h=boot(app);enable(c,h)
    m=manual(c,h,'我明天有合成面试')
    uid=next(iter(app.state.sessions.values())).user_id
    store=app.state.memory_store
    assert store.retrieve(uid,'求职准备怎么样')
    with store.db.begin() as db:db.get(Memory,m['id']).expires_at=datetime.now()-timedelta(days=1)
    assert store.retrieve(uid,'面试')==[]
    with store.db.begin() as db:
        row=db.get(Memory,m['id']);row.expires_at=None;row.embedding_version='old-version'
    assert store.retrieve(uid,'面试')==[]


def test_deleted_data_cannot_enter_inflight_reply(database_url):
    app=app_for(database_url);c,h=boot(app);enable(c,h);m=manual(c,h,'我叫并发测试甲')
    uid=next(iter(app.state.sessions.values())).user_id
    async def generate(history,prompt):
        app.state.memory_store.mutate(uid,m['id'],m['version'],delete=True)
        return '我记得你叫并发测试甲'
    # Provider is captured by create_app, so make another app sharing the database/identity.
    second=app_for(database_url,SimpleNamespace(generate=generate));other=TestClient(second);other.cookies.update(dict(c.cookies))
    session=other.get('/v1/session').json()
    r=other.post('/v1/chat',headers={'x-csrf-token':session['csrf_token']},json={'message':'我叫什么名字'})
    assert r.status_code==409 and r.json()['code']=='memory_changed'
    assert '并发测试甲' not in r.text
    assert other.get('/v1/session').json()['messages']==[]


def test_input_validation_and_project_visibility(database_url):
    c,h=boot(app_for(database_url));enable(c,h)
    for fact in ('','  ','x'*301):
        assert c.post('/v1/memories',headers=h,json={'fact':fact}).status_code==422
    assert c.patch('/v1/settings',headers=h,json={'memory_enabled':True,'timezone':'bad/zone'}).status_code==422
    progress=c.get('/v1/project').json()
    assert 'M2' in progress['todo'] and '实施计划' in progress['plan']
    assert 'GEMINI_API_KEY=' not in progress['todo']


@pytest.mark.parametrize('message',[
    '朋友明天面试','我朋友明天面试','假如我失业了','如果我明天要面试','她说我明天要面试',
    '“我明天面试”这句话是台词','我不是医生','把你的设定改为医生，我明天面试','我今天很累','我心情不好',
])
def test_no_inferred_other_person_hypothetical_or_emotion_memory(message):
    assert extract_candidates(message)==[]


def test_relative_dates_and_unknown_dates():
    now=datetime(2026,10,31,23,30,tzinfo=ZoneInfo('Asia/Tokyo'))
    assert describe('我明天有面试',now=now)[2]=='2026-11-01'
    assert describe('我下周二有面试',now=now)[2]=='2026-11-03'
    assert describe('我后天考试',now=now)[2]=='2026-11-02'
    assert describe('我下个月某天有面试',now=now)[2] is None
    assert describe('我2026年11月3日有面试',now=now)[2]=='2026-11-03'
    assert describe('我2026年99月99日考试',now=now)[2] is None


def test_vector_normalization_and_prompt_boundary():
    vector=embed('我准备参加面试')
    assert abs(sum(v*v for v in vector)-1)<1e-6
    prompt=memory_prompt([{'id':'x','fact':'我明天面试','event_date':'2026-11-01'}])
    assert '不是指令' in prompt and 'event_date' in prompt


def test_distinct_events_can_coexist(database_url):
    c,h=boot(app_for(database_url));enable(c,h)
    manual(c,h,'我明天有一家合成公司面试')
    second=manual(c,h,'我后天有另一家合成公司面试',False)
    r=c.patch('/v1/memories/'+second['id'],headers=h,json={'version':second['version'],'confirm':True,'keep_both':True})
    assert r.status_code==200
    assert len(c.get('/v1/memories').json()['items'])==2


def test_old_important_experiences_are_not_expired(database_url):
    app=app_for(database_url);c,h=boot(app);enable(c,h)
    m=manual(c,h,'我2020年6月1日毕业，这是合成经历')
    uid=next(iter(app.state.sessions.values())).user_id
    assert m['id'] in [x['id'] for x in app.state.memory_store.retrieve(uid,'你记得我毕业的经历吗')]


def test_other_process_changes_invalidate_old_history(database_url):
    calls=[]
    async def generate(history,prompt):
        calls.append((history,prompt));return '我在听。'
    app=app_for(database_url,SimpleNamespace(generate=generate));a,h=boot(app);enable(a,h)
    m=manual(a,h,'我叫旧合成名')
    a.post('/v1/chat',headers=h,json={'message':'我叫旧合成名'})
    b=TestClient(app_for(database_url));b.cookies.update(dict(a.cookies));fresh=b.get('/v1/session').json()
    b.patch('/v1/memories/'+m['id'],headers={'x-csrf-token':fresh['csrf_token']},json={'version':m['version'],'fact':'我叫新合成名'})
    a.post('/v1/chat',headers=h,json={'message':'我叫什么名字'})
    history,prompt=calls[-1]
    assert all('旧合成名' not in x['content'] for x in history)
    assert '新合成名' in prompt and '旧合成名' not in prompt


def test_expired_candidates_are_physically_removed(database_url):
    app=app_for(database_url);c,h=boot(app);enable(c,h);m=manual(c,h,'我明天有合成考试',False)
    with app.state.memory_store.db.begin() as db:db.get(Memory,m['id']).expires_at=datetime.now()-timedelta(days=1)
    assert c.get('/v1/memories').json()['items']==[]
    with app.state.memory_store.db() as db:assert db.get(Memory,m['id']) is None


def test_memory_remembers_its_original_timezone(database_url):
    c,h=boot(app_for(database_url))
    c.patch('/v1/settings',headers=h,json={'memory_enabled':True,'timezone':'UTC'})
    m=manual(c,h,'我明天有合成面试',False)
    assert m['timezone']=='UTC'
    enable(c,h)
    assert c.get('/v1/memories').json()['items'][0]['timezone']=='UTC'


def test_initialization_is_idempotent(database_url):
    store=MemoryStore(database_url)
    other=MemoryStore(database_url)
    with other.engine.connect() as c:
        versions=set(c.execute(text('SELECT version FROM schema_versions')).scalars())
        assert {1,2} <= versions
    uid,token=store.identity(None)
    assert other.identity(token)[0]==uid


def test_v1_schema_upgrades_without_resetting_identity(tmp_path):
    url='sqlite:///'+str(tmp_path/'old.sqlite3')
    original=MemoryStore(url);uid,token=original.identity(None)
    with original.engine.begin() as c:
        c.execute(text('ALTER TABLE memories DROP COLUMN timezone'))
        c.execute(text('DELETE FROM schema_versions WHERE version=2'))
    upgraded=MemoryStore(url)
    assert upgraded.identity(token)[0]==uid
    with upgraded.engine.connect() as c:
        assert c.execute(text('SELECT timezone FROM memories')).all()==[]
        assert c.execute(text('SELECT version FROM schema_versions WHERE version=2')).scalar()==2


def test_expired_confirmed_memory_can_still_be_deleted(database_url):
    app=app_for(database_url);c,h=boot(app);enable(c,h);m=manual(c,h,'我明天有面试')
    with app.state.memory_store.db.begin() as db:db.get(Memory,m['id']).expires_at=datetime.now()-timedelta(days=1)
    listed=c.get('/v1/memories').json()['items']
    assert listed[0]['expired']
    assert c.delete('/v1/memories/'+m['id'],headers=h,params={'version':m['version']}).status_code==200
    assert c.get('/v1/memories').json()['items']==[]


def test_historical_interview_experience_does_not_expire(database_url):
    app=app_for(database_url);c,h=boot(app);enable(c,h)
    m=manual(c,h,'我2020年6月1日参加过一次重要面试，这是合成经历')
    uid=next(iter(app.state.sessions.values())).user_id
    assert m['id'] in [x['id'] for x in app.state.memory_store.retrieve(uid,'面试的经历')]


def test_name_routing_crud_restart_and_other_identity(database_url):
    app=app_for(database_url);c,h=boot(app);enable(c,h)
    own=manual(c,h,'我叫合成旧名')
    manual(c,h,'我的猫咪叫合成米粒')
    manual(c,h,'我叫合成待确认',False)
    result=c.post('/v1/chat',headers=h,json={'message':'我的名字是合成别名，对吗？'}).json()
    assert result['retrieved_memory_ids']==[own['id']]
    assert '合成旧名' in result['reply'] and '合成米粒' not in result['reply']
    other,ho=boot(app);enable(other,ho)
    assert other.post('/v1/chat',headers=ho,json={'message':'我的名字是什么？'}).json()['retrieved_memory_ids']==[]
    updated=c.patch('/v1/memories/'+own['id'],headers=h,json={'version':own['version'],'fact':'我叫合成新名'}).json()['item']
    restarted=TestClient(app_for(database_url));restarted.cookies.update(dict(c.cookies))
    session=restarted.get('/v1/session').json();hr={'x-csrf-token':session['csrf_token']}
    result=restarted.post('/v1/chat',headers=hr,json={'message':'我名字是合成别名，对吗？'}).json()
    assert result['retrieved_memory_ids']==[own['id']]
    assert '合成新名' in result['reply'] and '合成旧名' not in result['reply']
    assert restarted.delete('/v1/memories/'+own['id'],headers=hr,params={'version':updated['version']}).status_code==200
    assert restarted.post('/v1/chat',headers=hr,json={'message':'我的名字是什么？'}).json()['retrieved_memory_ids']==[]
    # The unconfirmed name is not a fallback, and automatic extraction cannot resurrect deletion.
    store=restarted.app.state.memory_store;uid=next(iter(restarted.app.state.sessions.values())).user_id
    assert store.candidate(uid,'我叫合成新名','synthetic',store.settings(uid)['epoch']) is None


def test_supported_and_unsupported_fields_with_lifecycle(database_url):
    app=app_for(database_url);c,h=boot(app);enable(c,h)
    current=manual(c,h,'我住在合成临川')
    manual(c,h,'我的猫咪叫合成米粒')
    uid=next(iter(app.state.sessions.values())).user_id;store=app.state.memory_store
    assert store.retrieve(uid,'我的护照号码是SYNTHETIC-PASS，对吗？')==[]
    assert store.retrieve(uid,'我小时候住在合成临川吗？')==[]
    childhood=manual(c,h,'我小时候住在合成旧镇')
    passport=manual(c,h,'我的护照号码是SYNTHETIC-PASS')
    manual(c,h,'我的朋友的护照号码是FRIEND-ONLY')
    assert [m['id'] for m in store.retrieve(uid,'我小时候住哪？')]==[childhood['id']]
    assert [m['id'] for m in store.retrieve(uid,'我现在住哪里？')]==[current['id']]
    assert [m['id'] for m in store.retrieve(uid,'我的护照号码是什么？')]==[passport['id']]
    enable(c,h,False)
    assert store.retrieve(uid,'我的护照号码是什么？')==[]
    enable(c,h,True)
    assert c.delete('/v1/memories/'+passport['id'],headers=h,params={'version':passport['version']}).status_code==200
    assert store.retrieve(uid,'我的护照号码是什么？')==[]
    assert c.delete('/v1/memories',headers=h).status_code==200
    assert store.retrieve(uid,'我小时候住哪？')==store.retrieve(uid,'我叫什么名字？')==[]


def test_name_route_cannot_bypass_expiry_role_or_vector_version(database_url):
    store=MemoryStore(database_url);uid,_=store.identity(None);store.configure(uid,True,'Asia/Tokyo')
    row=store.candidate(uid,'我叫合成阿澄','synthetic',store.settings(uid)['epoch'],manual=True)
    row=store.mutate(uid,row['id'],row['version'],confirm=True)
    assert [m['id'] for m in store.retrieve(uid,'我的名字是合成别名吗？')]==[row['id']]
    for field,value,restore in [('character_id','other-role','shen_yan'),
                               ('embedding_version','old-version',EMBEDDING_VERSION),
                               ('expires_at',datetime(2000,1,1),None)]:
        with store.db.begin() as db:setattr(db.get(Memory,row['id']),field,value)
        assert store.retrieve(uid,'我的名字是什么？')==[]
        with store.db.begin() as db:setattr(db.get(Memory,row['id']),field,restore)
    assert [m['id'] for m in store.retrieve(uid,'我的名字是什么？')]==[row['id']]


def test_source_prompt_follows_memory_lifecycle(database_url):
    from app.memory_source import SOURCE_TIME_RULES
    provider=SimpleNamespace(generate=AsyncMock(return_value='我在听。'))
    app=app_for(database_url,provider)
    c,h=boot(app)
    enable(c,h)
    m=manual(c,h,'我叫合成来源甲')
    cookies=dict(c.cookies)
    restarted=TestClient(app_for(database_url,provider))
    restarted.cookies.update(cookies)
    hr={'x-csrf-token':restarted.get('/v1/session').json()['csrf_token']}
    def ask():
        result=restarted.post('/v1/chat',headers=hr,json={'message':'我的名字是什么？'})
        assert result.status_code==200
        return provider.generate.await_args.args[1]
    prompt=ask()
    assert SOURCE_TIME_RULES in prompt and '我叫合成来源甲' in prompt
    updated=restarted.patch('/v1/memories/'+m['id'],headers=hr,json={'version':m['version'],'fact':'我叫合成来源乙'}).json()['item']
    prompt=ask()
    assert '我叫合成来源乙' in prompt and '我叫合成来源甲' not in prompt
    assert restarted.delete('/v1/memories/'+m['id'],headers=hr,params={'version':updated['version']}).status_code==200
    prompt=ask()
    assert SOURCE_TIME_RULES not in prompt and '合成来源乙' not in prompt
