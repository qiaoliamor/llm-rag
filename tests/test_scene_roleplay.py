"""Fiction license admission tests; fake labels are not semantic eval results."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx2
import pytest
from fastapi.testclient import TestClient
from app.config import ROOT,Settings
from app.dialogue import CHARACTER,SCENE_PROFILE,instructions
from app.main import create_app
from app.semantic_review import ModelAnalysisProvider,INDEXED_PROMPT,evidence_bundle


def verdict(text,*,ids=None,unsupported=False):
    return {'decision':'revise' if unsupported else 'accept','confidence':.95,'segments':[{
        'text':text,'kind':'assertion','verdict':'unsupported' if unsupported else 'supported',
        'evidence_ids':ids if ids is not None else [] if unsupported else ['scene_profile'],
        'reason':'missing_evidence' if unsupported else 'evidence_supports'}]}


def make(tmp_path,provider,judge):
    app=create_app(Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'scene.sqlite3')),
                   provider,semantic_judge=judge)
    client=TestClient(app)
    headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
    return client,headers


def test_background_is_separate_versioned_license_not_new_canon():
    assert CHARACTER['version']=='1.2' and len(CHARACTER['canon'])==4
    assert SCENE_PROFILE==json.loads((ROOT/'characters/shen_yan_scene.json').read_text())
    for mode in ('canon','rag','direct'):
        prompt=instructions(mode)
        assert '虚构书店场景与叙事许可' in prompt and SCENE_PROFILE['environment'] in prompt
    bundle=evidence_bundle([{'role':'user','content':'你好'}],[],None,None)
    item=next(e for e in bundle if e['id']=='scene_profile')
    assert item['kind']=='fictional_scene_license' and item['data']==SCENE_PROFILE
    assert '具体收货' in INDEXED_PROMPT and '角色身世' not in item['data']['environment']


@pytest.mark.parametrize('text',[
    '今天店里很安静，书页轻轻地响。','窗外这会儿倒是挺安静的。',
    '暖灯亮着，手边摊着一本书。',
])
def test_supported_licensed_atmosphere_is_not_rewritten(tmp_path,text):
    provider=SimpleNamespace(generate=AsyncMock(return_value=text))
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(text)))
    client,headers=make(tmp_path,provider,judge)
    response=client.post('/v1/chat',headers=headers,json={'message':'你店里今天安静吗？'})
    assert response.status_code==200 and response.json()['reply']==text
    assert response.json()['semantic_review']['status']=='accepted'
    assert provider.generate.await_count==judge.review.await_count==1
    assert response.json()['memory_candidates']==[]


@pytest.mark.parametrize('bad',[
    '刚收到十箱你寄来的书。','也没收到什么新的消息。','你今天过来，是想找书吗？',
    '具体近况我还不能确定。','北京现在5度，出门多穿点。',
])
def test_events_player_presupposition_and_wrong_owner_voice_are_rewritten(tmp_path,bad):
    good='店里这会儿挺安静，正好聊聊书。'
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[bad,good]))
    judge=SimpleNamespace(review=AsyncMock(side_effect=[verdict(bad,unsupported=True),verdict(good)]))
    client,headers=make(tmp_path,provider,judge)
    response=client.post('/v1/chat',headers=headers,json={'message':'你好'})
    assert response.json()['reply']==good
    assert provider.generate.await_count==judge.review.await_count==2
    assert bad not in str(client.get('/v1/session').json()['messages'])
    rewrite=provider.generate.call_args_list[1].args[1]
    assert '保留场景设定授权' in rewrite and '不知道自家店况' in rewrite


def test_scene_citation_cannot_override_hard_canon(tmp_path):
    bad='我今年19岁。'
    provider=SimpleNamespace(generate=AsyncMock(return_value=bad))
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(bad)))
    client,headers=make(tmp_path,provider,judge)
    response=client.post('/v1/chat',headers=headers,json={'message':'你好'})
    assert response.json()['reply']!=bad and response.json()['guarded']
    assert provider.generate.await_count==2


def test_scene_citation_cannot_override_existing_weather_tool_guard():
    from app.reply_pipeline import generate_checked
    bad='明天13到20度。'
    tool={'status':'ok','kind':'forecast','source':'Open-Meteo','min_c':12,'max_c':18}
    provider=SimpleNamespace(generate=AsyncMock(return_value=bad))
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(bad)))
    reply,guarded,_=asyncio.run(generate_checked(provider,[],'prompt','天气',[],tool,None,{},judge=judge))
    assert reply!=bad and guarded and provider.generate.await_count==2


def test_unavailable_review_does_not_let_unreviewed_atmosphere_through(tmp_path):
    text='店里这会儿挺安静。'
    provider=SimpleNamespace(generate=AsyncMock(return_value=text))
    judge=SimpleNamespace(review=AsyncMock(side_effect=TimeoutError()))
    client,headers=make(tmp_path,provider,judge)
    response=client.post('/v1/chat',headers=headers,json={'message':'你好'})
    assert response.json()['reply']!=text
    assert response.json()['semantic_review']['failure']=='timeout'
    assert text not in str(client.get('/v1/session').json()['messages'])


def test_sdk_sends_bounded_assistant_context_as_non_player_evidence():
    seen=[]
    def handler(request):
        payload=json.loads(request.content);data=json.loads(payload['messages'][1]['content']);seen.append(data)
        assert len(data['fictional_dialogue_context'])==4
        assert all(set(m)=={'role','content'} for m in data['fictional_dialogue_context'])
        assert not any(e.get('text','').startswith('虚构玩家姓名') for e in data['evidence'])
        output={'confidence':.95,'units':[{'id':'u0','kind':'assertion','verdict':'supported','evidence_ids':['scene_profile']}]}
        return httpx2.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'test',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(output)}}]})
    async def check():
        config=Settings(_env_file=None,chat_provider='gemini',gemini_api_key='test-key')
        judge=ModelAnalysisProvider(config,httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
        history=[{'role':'assistant','content':f'虚构玩家姓名{i}','internal':'omit'} for i in range(6)]+[{'role':'user','content':'你好'}]
        result=await judge.review('店里安静。',history,evidence_bundle(history,[],None,None))
        assert result.decision=='accept'
    asyncio.run(check());assert len(seen)==1


@pytest.mark.parametrize('generation_ok,expected_attempts',[(True,3),(False,2)])
def test_targeted_retest_is_capped_and_never_retries(monkeypatch,generation_ok,expected_attempts):
    from scripts import retest_scene_roleplay as script
    from app.semantic_review import ReviewOutcome
    from app.dialogue import ProviderFailure
    judge=AsyncMock(return_value=ReviewOutcome('unavailable',None,'upstream_unavailable'))
    generator=AsyncMock(return_value='店里挺安静。',side_effect=None if generation_ok else ProviderFailure('rate_limit','private-upstream',429))
    monkeypatch.setattr(script,'review_reply',judge)
    monkeypatch.setattr(script.GeminiProvider,'generate',generator)
    report=asyncio.run(script.retest(Settings(_env_file=None,chat_provider='gemini'),interval=0))
    assert report['attempts']==expected_attempts and report['max_attempts']==3
    assert generator.await_count==1 and judge.await_count==(2 if generation_ok else 1)
    assert 'private-upstream' not in str(report)
    import subprocess,sys,os
    result=subprocess.run([sys.executable,'scripts/retest_scene_roleplay.py'],cwd=ROOT,
        env={**os.environ,'CHAT_PROVIDER':'invalid'},capture_output=True,text=True)
    assert result.returncode==2 and '显式--live' in result.stderr


def test_old_reference_labels_are_not_rebranded_as_scene_licensed_quality():
    from app.fact_support_evaluation import evaluate
    report=evaluate()
    assert report['scene_policy']=='legacy-strict-no-fiction-license'
    assert 'not current roleplay quality' in report['limits'][0]
