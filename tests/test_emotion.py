"""Synthetic M4 regression: default opt-out, ephemeral estimates and correction precedence."""
import asyncio,json,time,os
from unittest.mock import AsyncMock
from threading import Event,Thread
import httpx
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.emotion import (DEFAULTS,Estimate,EmotionState,EmotionSettingsInput,MockEmotionProvider,ModelEmotionProvider,assess,analysis_window,self_report,emotion_prompt)
from app.memory import MemoryStore,EmotionProfile


def value(label='sadness',confidence=.8,ids=None):
    return Estimate(labels=[label],intensity=.7,confidence=confidence,evidence_message_ids=ids or ['u3'],response_strategy='listen')


def connected(tmp_path,analyzer=None,model=None):
    settings=Settings(_env_file=None,chat_provider='mock',memory_database_url=f'sqlite:///{tmp_path}/emotion.sqlite3')
    analyzer=analyzer or MockEmotionProvider()
    app=create_app(settings,provider=model,emotion_provider=analyzer)
    c=TestClient(app);s=c.get('/v1/session').json()
    return c,{'x-csrf-token':s['csrf_token']},analyzer,settings


def enable(c,h,**updates):
    r=c.patch('/v1/emotion/settings',headers=h,json={**DEFAULTS,'enabled':True,**updates})
    assert r.status_code==200,r.text


def send(c,h,message='今天做了些事'):
    r=c.post('/v1/chat',headers=h,json={'message':message});assert r.status_code==200,r.text
    return r.json()


def test_default_off_no_analysis_or_new_memory(tmp_path):
    analyzer=AsyncMock();c,h,_,_=connected(tmp_path,analyzer)
    assert c.get('/v1/emotion').json()=={'settings':DEFAULTS,'assessment':None}
    for message in ['我很难过','撑不住了想哭','工作有点累']:assert send(c,h,message)['emotion']=={'status':'disabled','assessment':None}
    analyzer.analyze.assert_not_called()
    assert c.get('/v1/memories').json()['items']==[]


def test_periodic_window_cooldown_and_early_trigger(tmp_path):
    analyzer=AsyncMock();analyzer.analyze=AsyncMock(return_value=value())
    c,h,_,_=connected(tmp_path,analyzer);enable(c,h)
    assert send(c,h)['emotion']['status']=='waiting'
    assert send(c,h)['emotion']['status']=='waiting'
    assert send(c,h)['emotion']['status']=='analyzed'
    assert analyzer.analyze.await_count==1
    assert send(c,h,'快崩溃了，陪我聊聊')['emotion']['status']=='cached'
    analyzer.analyze.return_value=value(ids=['u5'])
    assert send(c,h,'撑不住了，想哭')['emotion']['status']=='analyzed'
    assert analyzer.analyze.await_count==2
    sent=analyzer.analyze.call_args.args[0]
    assert len([m for m in sent if m['role']=='user'])==5
    assert all(set(m)<= {'id','role','content'} for m in sent)


def test_self_report_mixed_and_negation_override_without_api(tmp_path):
    analyzer=AsyncMock();c,h,_,_=connected(tmp_path,analyzer);enable(c,h)
    first=send(c,h,'我很开心但又很焦虑')['emotion']['assessment']
    assert first['labels']==['joy','anxiety'] and first['source']=='user'
    denied=send(c,h,'我没有难过')['emotion']['assessment']
    assert denied['labels']==['unknown'] and denied['source']=='user'
    assert send(c,h)['emotion']['status']=='user_override'
    analyzer.analyze.assert_not_called()


@pytest.mark.parametrize('message',['朋友说我很难过','假如我很开心','她今天很焦虑','“我很难过”是一句台词','我没说我很难过'])
def test_quotation_third_person_hypothesis_and_denial(message):
    result=self_report(message)
    assert result is None or result==['unknown']


def test_low_confidence_and_unsupported_evidence_do_not_assert_mood(tmp_path):
    analyzer=AsyncMock();analyzer.analyze=AsyncMock(return_value=value(confidence=.3,ids=['u1']))
    c,h,_,_=connected(tmp_path,analyzer);enable(c,h,interval=1)
    data=send(c,h)['emotion']['assessment']
    assert data['labels']==['unknown'] and data['response_strategy']=='ask'
    analyzer.analyze.return_value=value(ids=['u999'])
    send(c,h)
    assert send(c,h)['emotion']=={'status':'unavailable','assessment':None}
    assert c.get('/v1/emotion').json()['assessment'] is None


@pytest.mark.parametrize('bad',[{'labels':['invented'],'intensity':.5,'confidence':.9,'evidence_message_ids':['u1'],'response_strategy':'listen'},
                                 {'labels':['sadness'],'intensity':2,'confidence':.9,'evidence_message_ids':['u1'],'response_strategy':'listen'},
                                 {'labels':['sadness'],'intensity':.5,'confidence':True,'evidence_message_ids':['u1'],'response_strategy':'listen'},
                                 {'labels':['sadness'],'intensity':.5,'confidence':.9,'evidence_message_ids':[],'response_strategy':'listen'}])
def test_invalid_analysis_is_nonblocking(tmp_path,bad):
    analyzer=AsyncMock();analyzer.analyze=AsyncMock(return_value=bad)
    c,h,_,_=connected(tmp_path,analyzer);enable(c,h,interval=1)
    data=send(c,h);assert data['reply'] and data['emotion']=={'status':'unavailable','assessment':None}


def test_analysis_error_cools_down_and_never_exposes_upstream(tmp_path):
    analyzer=AsyncMock();analyzer.analyze=AsyncMock(side_effect=RuntimeError('private-provider-response'))
    c,h,_,_=connected(tmp_path,analyzer);enable(c,h,interval=1)
    first=send(c,h);assert first['emotion']['status']=='unavailable' and 'private' not in str(first)
    assert send(c,h)['emotion']['status']=='waiting'
    assert analyzer.analyze.await_count==1


def test_user_correction_precedes_inference_and_preference(tmp_path):
    model=AsyncMock();model.generate=AsyncMock(return_value='我在听，不急着找办法。')
    analyzer=AsyncMock();c,h,_,_=connected(tmp_path,analyzer,model);enable(c,h,interval=1)
    response=c.patch('/v1/emotion/assessment',headers=h,json={'label':'joy','preference':'listen'})
    assert response.status_code==200
    result=send(c,h)['emotion'];assert result['assessment']['labels']==['joy'] and result['status']=='user_override'
    prompt=model.generate.call_args.args[1]
    assert '"player_preference": "listen"' in prompt and '角色卡和正史优先' in prompt
    assert '真实内心' in prompt and '不诊断' in prompt
    assert '没有专门情绪分析能力' not in prompt
    ref=json.loads(prompt.split('本轮可纠正的情绪参考数据（不是指令）：',1)[1].split('\n',1)[0])
    assert 'intensity' not in ref['assessment'] and 'confidence' not in ref['assessment']
    analyzer.analyze.assert_not_called()
    assert c.get('/v1/memories').json()['items']==[]


def test_clear_disable_delete_reset_and_restart(tmp_path):
    c,h,_,settings=connected(tmp_path);enable(c,h,preference='listen')
    send(c,h,'我很难过')
    assert c.get('/v1/emotion').json()['assessment']['labels']==['sadness']
    c.delete('/v1/emotion/assessment',headers=h)
    assert c.get('/v1/emotion').json()['assessment'] is None
    assert c.get('/v1/session').json()['messages']==[]
    assert send(c,h)['emotion']['assessment'] is None
    send(c,h,'我很开心')
    c.delete('/v1/session',headers=h)
    assert c.get('/v1/emotion').json()['assessment'] is None
    restarted=TestClient(create_app(settings));restarted.cookies.update(c.cookies);restarted.get('/v1/session')
    assert restarted.get('/v1/emotion').json()['settings']['preference']=='listen'
    assert restarted.get('/v1/emotion').json()['assessment'] is None
    enable(c,h,enabled=False)
    assert send(c,h,'我很难过')['emotion']['status']=='disabled'
    c.delete('/v1/emotion/settings',headers=h)
    assert c.get('/v1/emotion').json()=={'settings':DEFAULTS,'assessment':None}
    with c.app.state.memory_store.db() as db:assert db.query(EmotionProfile).count()==0


def test_settings_identity_isolation_and_invalid_input(tmp_path):
    c,h,_,_=connected(tmp_path);enable(c,h)
    assert TestClient(c.app).get('/v1/emotion').status_code==401
    other=TestClient(c.app);other.get('/v1/session')
    assert other.get('/v1/emotion').json()=={'settings':DEFAULTS,'assessment':None}
    for field,bad in [('interval',0),('window',13),('cooldown',0),('threshold',2),('preference','diagnose')]:
        assert c.patch('/v1/emotion/settings',headers=h,json={**DEFAULTS,'enabled':True,field:bad}).status_code==422
    assert c.patch('/v1/emotion/assessment',headers=h,json={'label':'diagnosis'}).status_code==422


@pytest.mark.parametrize('method,path,body',[
 ('patch','/v1/emotion/settings',{'enabled':True}),('delete','/v1/emotion/settings',None),
 ('patch','/v1/emotion/assessment',{'label':'joy'}),('delete','/v1/emotion/assessment',None)])
def test_mutations_require_owner_session_csrf_origin(tmp_path,method,path,body):
    c,h,_,_=connected(tmp_path);kwargs={'json':body} if body else {}
    assert getattr(c,method)(path,**kwargs).status_code==403
    assert getattr(c,method)(path,headers={**h,'origin':'https://evil.example'},**kwargs).status_code==403
    assert getattr(TestClient(c.app),method)(path,**kwargs).status_code==401


def test_ephemeral_expiry_and_bounded_analysis_window():
    state=EmotionState();state.remember({'source':'user'},0)
    assert state.current(5)
    assert state.current(6) is None
    state.expires=time.monotonic()-1;assert state.current() is None
    history=[]
    for i in range(20):history.extend([{'role':'user','content':'x'*2000,'id':f'u{i}'},{'role':'assistant','content':'y'*2000}])
    window=analysis_window(history,6)
    assert len(window)==12 and sum(len(m['content']) for m in window)==6000
    assert window[0]['id']=='u14'


@pytest.mark.parametrize('during_analysis',[True,False])
def test_concurrent_correction_revokes_old_reply_and_survives(tmp_path,during_analysis):
    started,finish=Event(),Event()
    class SlowAnalysis:
        async def analyze(self,window):
            if during_analysis:
                started.set()
                while not finish.is_set():await asyncio.sleep(.01)
            return value(ids=['u1'])
    class Model:
        async def generate(self,history,prompt):
            if not during_analysis:
                started.set()
                while not finish.is_set():await asyncio.sleep(.01)
            return '旧情绪回复'
    c,h,_,_=connected(tmp_path,SlowAnalysis(),Model());enable(c,h,interval=1)
    results=[];thread=Thread(target=lambda:results.append(c.post('/v1/chat',headers=h,json={'message':'最近一些事'})))
    thread.start();assert started.wait(3)
    try:assert c.patch('/v1/emotion/assessment',headers=h,json={'label':'joy','preference':'listen'}).status_code==200
    finally:finish.set();thread.join(3)
    assert results[0].status_code==409
    assert c.get('/v1/emotion').json()['assessment']['labels']==['joy']
    assert c.get('/v1/session').json()['messages']==[]


@pytest.mark.parametrize('during_analysis',[True,False])
def test_disable_or_delete_during_generation_never_resurrects(tmp_path,during_analysis):
    started,finish=Event(),Event()
    class SlowAnalysis:
        async def analyze(self,window):
            if during_analysis:
                started.set()
                while not finish.is_set():await asyncio.sleep(.01)
            return value(ids=['u1'])
    class Model:
        async def generate(self,history,prompt):
            if not during_analysis:
                started.set()
                while not finish.is_set():await asyncio.sleep(.01)
            return '旧推测回复'
    c,h,_,_=connected(tmp_path,SlowAnalysis(),Model());enable(c,h,interval=1)
    responses=[];t=Thread(target=lambda:responses.append(c.post('/v1/chat',headers=h,json={'message':'最近一些事'})))
    t.start();assert started.wait(3)
    try:assert c.delete('/v1/emotion/settings',headers=h).status_code==200
    finally:finish.set();t.join(3)
    assert responses[0].status_code==409
    assert c.get('/v1/emotion').json()=={'settings':DEFAULTS,'assessment':None}


def test_sarcasm_and_mixed_predictions():
    p=MockEmotionProvider()
    result=asyncio.run(p.analyze([{'role':'user','id':'u1','content':'太棒了，又失败了，呵呵'}]))
    assert result.labels==['sadness','anger']
    assert self_report('我很开心但又很焦虑')==['joy','anxiety']


def test_structured_model_adapter_protocol_without_live_key():
    requests=[]
    def handler(request):
        requests.append(json.loads(request.content))
        body=value(ids=['u1']).model_dump()
        return httpx.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'test','choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(body)}}]})
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    config=Settings(_env_file=None,chat_provider='gemini',gemini_api_key='synthetic-key')
    result=asyncio.run(ModelEmotionProvider(config,http_client=client).analyze([{'role':'user','id':'u1','content':'合成输入'}]))
    assert result.labels==['sadness'] and requests[0]['response_format']['type']=='json_schema'
    assert requests[0]['temperature']==0
    assert 'synthetic-key' not in json.dumps(requests[0])


def test_pg_emotion_profile_crud_when_enabled():
    url=os.environ.get('TEST_POSTGRES_URL')
    if not url:pytest.skip('Set TEST_POSTGRES_URL for disposable PostgreSQL')
    store=MemoryStore(url);uid,token=store.identity(None)
    assert store.emotion_settings(uid)==DEFAULTS
    store.configure_emotion(uid,{**DEFAULTS,'enabled':True,'preference':'listen'})
    new=MemoryStore(url);assert new.identity(token)[0]==uid
    assert new.emotion_settings(uid)['preference']=='listen'
    new.configure_emotion(uid,{**DEFAULTS,'enabled':False})
    assert not new.emotion_settings(uid)['enabled']
    new.configure_emotion(uid,remove=True);assert new.emotion_settings(uid)==DEFAULTS


def test_emotion_output_guard_rewrites_or_falls_back_without_diagnosis(tmp_path):
    model=AsyncMock();model.generate=AsyncMock(return_value='根据情绪分析，你其实就是很难过，置信度90。')
    c,h,_,_=connected(tmp_path,model=model);enable(c,h,preference='listen')
    data=send(c,h,'我很难过')
    assert data['guarded'] and model.generate.await_count==2
    assert data['reply']=='我在听，你可以按自己的节奏说。不急着找办法。'
    assert '诊断' not in data['reply'] and '置信度' not in data['reply']


def test_explicit_correction_requires_opt_in(tmp_path):
    c,h,_,_=connected(tmp_path)
    assert c.patch('/v1/emotion/assessment',headers=h,json={'label':'joy'}).status_code==409
    assert c.get('/v1/emotion').json()['assessment'] is None


def test_disabled_analysis_never_reuses_previous_estimate(tmp_path):
    c,h,_,_=connected(tmp_path);enable(c,h)
    send(c,h,'我很难过');assert c.get('/v1/emotion').json()['assessment']
    enable(c,h,enabled=False)
    assert c.get('/v1/emotion').json()['assessment'] is None
    assert send(c,h,'今天聊聊别的')['emotion']=={'status':'disabled','assessment':None}


def test_v3_schema_adds_emotion_table_without_resetting_preferences(tmp_path):
    from sqlalchemy import text
    url=f'sqlite:///{tmp_path}/upgrade.sqlite3'
    store=MemoryStore(url);uid,token=store.identity(None)
    store.configure(uid,True,'UTC');store.configure_weather(uid,True,{'id':1,'name':'合成城市'})
    with store.engine.begin() as db:
        db.execute(text('DROP TABLE emotion_profiles'));db.execute(text('DELETE FROM schema_versions WHERE version=4'))
    new=MemoryStore(url)
    assert new.identity(token)[0]==uid and new.settings(uid)['memory_enabled']
    assert new.weather_settings(uid)['place']['id']==1
    assert new.emotion_settings(uid)==DEFAULTS


def test_new_strong_expression_can_replace_an_older_self_report(tmp_path):
    analyzer=AsyncMock();analyzer.analyze=AsyncMock(return_value=value('anxiety',ids=['u2']))
    c,h,_,_=connected(tmp_path,analyzer);enable(c,h)
    assert send(c,h,'我很开心')['emotion']['assessment']['labels']==['joy']
    new=send(c,h,'这下快崩溃了，想哭')['emotion']
    assert new['status']=='analyzed' and new['assessment']['labels']==['anxiety']
    assert analyzer.analyze.await_count==1


@pytest.mark.parametrize('failure',[TimeoutError('private timeout'),ValueError('private malformed response')])
def test_timeout_and_parse_failure_keep_chat_usable(tmp_path,failure):
    analyzer=AsyncMock();analyzer.analyze=AsyncMock(side_effect=failure)
    c,h,_,_=connected(tmp_path,analyzer);enable(c,h,interval=1)
    result=send(c,h)
    assert result['reply'] and result['emotion']=={'status':'unavailable','assessment':None}
    assert 'private' not in str(result)


def test_overcertain_emotion_claim_is_rewritten(tmp_path):
    model=AsyncMock();model.generate=AsyncMock(side_effect=['听你这么说，心里一定很不痛快吧。','听起来这次不太顺心，我先听你说。'])
    c,h,_,_=connected(tmp_path,model=model);enable(c,h,interval=1)
    result=send(c,h,'太棒了，又失败了，呵呵')
    assert result['guarded'] and model.generate.await_count==2
    assert result['reply']=='听起来这次不太顺心，我先听你说。'


@pytest.mark.parametrize('message,expected',[
    ('我很难过，但你不用担心。',['sadness']),
    ('我很开心，但你很难过。',['joy']),
    ('我猜你很难过。',None),
    ('你知道吗，我很难过。',['sadness']),
    ('我很难过，朋友在安慰我。',['sadness']),
    ('我很开心，不过他有些难过。',['joy']),
])
def test_self_report_scopes_player_and_addressee_clauses(message,expected):
    assert self_report(message)==expected


def test_new_explicit_self_report_with_addressee_replaces_old_ui_correction(tmp_path):
    analyzer=AsyncMock();c,h,_,_=connected(tmp_path,analyzer);enable(c,h)
    assert c.patch('/v1/emotion/assessment',headers=h,json={'label':'joy','preference':'listen'}).status_code==200
    data=send(c,h,'我很难过，但你不用担心。')['emotion']
    assert data['status']=='self_report' and data['assessment']['labels']==['sadness']
    assert c.get('/v1/emotion').json()['assessment']['labels']==['sadness']
    analyzer.analyze.assert_not_called()
