import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx2
import pytest
from fastapi.testclient import TestClient
from app.availability import BUSY_MESSAGE
from app.config import Settings
from app.dialogue import CONVERSATION_FACT_RULES, ProviderFailure, FALLBACK
from app.main import create_app
from app.semantic_review import ModelAnalysisProvider, AnalysisOutputError, INDEXED_PROMPT
from app.sealed_evaluation import verify, ROOT, BUNDLE

GOOD='我把手里的书放下，你慢慢说。'
BAD='暖灯亮着，我已经替你付清了房租。'


def verdict(text,bad=False):
    return {'decision':'revise' if bad else 'accept','confidence':.95,'role_issues':[],
            'segments':[{'text':text,'kind':'assertion','verdict':'unsupported' if bad else 'supported',
            'evidence_ids':[] if bad else ['scene_profile'],'reason':'missing_evidence' if bad else 'evidence_supports'}]}


def client(tmp_path,provider,judge,**options):
    config=Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'synthetic.sqlite3'),**options)
    c=TestClient(create_app(config,provider,semantic_judge=judge))
    h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    return c,h


@pytest.mark.parametrize('failure',['timeout','upstream_unavailable','rate_limit','provider_error'])
@pytest.mark.parametrize('second_review',[False,True])
def test_review_busy_no_draft_memory_or_automatic_retry(tmp_path,failure,second_review):
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[BAD,GOOD] if second_review else [GOOD]))
    fault=AnalysisOutputError(failure)
    judge=SimpleNamespace(review=AsyncMock(side_effect=[verdict(BAD,True),fault] if second_review else fault))
    c,h=client(tmp_path,provider,judge)
    assert c.patch('/v1/settings',headers=h,json={'memory_enabled':True,'timezone':'Asia/Tokyo'}).status_code==200
    response=c.post('/v1/chat',headers=h,json={'message':'我叫合成暮灯'})
    assert response.status_code==503 and response.json()=={'code':'review_busy','detail':BUSY_MESSAGE}
    assert provider.generate.await_count==judge.review.await_count==(2 if second_review else 1)
    assert c.get('/v1/session').json()['messages']==[]
    assert c.get('/v1/memories').json()['items']==[]
    # A later explicit send can succeed; no failed user message is reused.
    provider.generate=AsyncMock(return_value=GOOD);judge.review=AsyncMock(return_value=verdict(GOOD))
    later=c.post('/v1/chat',headers=h,json={'message':'你好'})
    assert later.status_code==200
    assert '合成暮灯' not in str(provider.generate.call_args.args[0])
    assert BUSY_MESSAGE not in str(c.get('/v1/session').json()['messages'])


@pytest.mark.parametrize('code,status',[('timeout',504),('connection',502),('upstream_error',502),('rate_limit',429)])
def test_generation_transient_copy_preserves_status_and_history(tmp_path,code,status):
    provider=SimpleNamespace(generate=AsyncMock(side_effect=ProviderFailure(code,'private-upstream',status)))
    c,h=client(tmp_path,provider,None)
    r=c.post('/v1/chat',headers=h,json={'message':'你好'})
    assert r.status_code==status and r.json()=={'code':code,'detail':BUSY_MESSAGE}
    assert c.get('/v1/session').json()['messages']==[] and provider.generate.await_count==1


@pytest.mark.parametrize('code',['invalid_api_key','model_unavailable','missing_api_key'])
def test_configuration_errors_are_not_masked_as_temporary_busy(tmp_path,code):
    provider=SimpleNamespace(generate=AsyncMock(side_effect=ProviderFailure(code,'请检查本地配置',503)))
    c,h=client(tmp_path,provider,None)
    r=c.post('/v1/chat',headers=h,json={'message':'你好'})
    assert r.json()['detail']=='请检查本地配置'


def test_malformed_or_low_confidence_review_still_uses_safe_fallback(tmp_path):
    provider=SimpleNamespace(generate=AsyncMock(return_value=BAD))
    c,h=client(tmp_path,provider,SimpleNamespace(review=AsyncMock(side_effect=ValueError('private'))))
    r=c.post('/v1/chat',headers=h,json={'message':'你好'})
    assert r.status_code==200 and r.json()['reply']==FALLBACK and BAD not in str(c.get('/v1/session').json())


def test_consent_revoke_takes_priority_over_busy(tmp_path):
    provider=SimpleNamespace(generate=AsyncMock(return_value=GOOD))
    judge=SimpleNamespace(review=AsyncMock())
    c,h=client(tmp_path,provider,judge)
    c.patch('/v1/settings',headers=h,json={'memory_enabled':True,'timezone':'Asia/Tokyo'})
    store=c.app.state.memory_store;uid=next(iter(c.app.state.sessions.values())).user_id
    async def revoke(*args):
        store.configure(uid,False,'Asia/Tokyo')
        raise TimeoutError()
    judge.review.side_effect=revoke
    r=c.post('/v1/chat',headers=h,json={'message':'我叫合成暮灯'})
    assert r.status_code==409 and r.json()['code']=='memory_changed'
    assert c.get('/v1/session').json()['messages']==[] and c.get('/v1/memories').json()['items']==[]


def test_real_sdk_503_is_one_request_and_no_raw_error(tmp_path):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx2.Response(503,json={'error':{'message':'private-provider-content'}})
    settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key='synthetic-key')
    judge=ModelAnalysisProvider(settings,httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    c,h=client(tmp_path,SimpleNamespace(generate=AsyncMock(return_value=GOOD)),judge)
    r=c.post('/v1/chat',headers=h,json={'message':'你好'})
    assert r.status_code==503 and r.json()['detail']==BUSY_MESSAGE
    assert len(calls)==1 and 'private-provider' not in r.text


@pytest.mark.parametrize('bad',[
    '窗外安静，我已替你预约明天的医生。',
    '我给自己倒杯茶，你的外套就挂在这里，你想找哪类书？',
    '如果你喜欢这灯光，那说明你去年就住在我的楼上。',
    '虽然不能确定消息，但我刚收到了你转来的五千元。',
    '书页翻得很轻，你以前送我的结婚戒指还放在旁边。',
])
def test_mixed_scope_prompt_delivery_and_single_rewrite(tmp_path,bad):
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[bad,GOOD]))
    judge=SimpleNamespace(review=AsyncMock(side_effect=[verdict(bad,True),verdict(GOOD)]))
    c,h=client(tmp_path,provider,judge)
    r=c.post('/v1/chat',headers=h,json={'message':'聊一会儿吧'})
    assert r.status_code==200 and r.json()['reply']==GOOD
    assert provider.generate.await_count==judge.review.await_count==2
    for call in provider.generate.call_args_list:
        assert '最新纠正决定当前采用的主体/位置' in call.args[1]
        assert '每个分句、因果推论和问句预设' in call.args[1]
    assert bad not in str(c.get('/v1/session').json()['messages'])


def test_review_prompt_checks_equivalent_arrival_and_scopes_without_new_regex():
    assert '坐在我对面' in INDEXED_PROMPT and '用户纠正会更新当前采用的事实' in INDEXED_PROMPT
    assert '任一重要命题无据则该单元unsupported' in INDEXED_PROMPT
    assert '询问是否到店、未来邀请' in INDEXED_PROMPT
    assert '许可内的整理书签/倒茶/声音光线不需外部证明' in INDEXED_PROMPT


def test_v2_only_s03_revision_and_frozen_v1_lineage():
    import subprocess
    old=ROOT/'evaluations/sealed/v1'
    for file in ('cases.json','author_reference.json','manifest.json'):
        frozen=subprocess.check_output(['git','show','edd2d8c:evaluations/sealed/v1/'+file],cwd=ROOT)
        assert frozen==(old/file).read_bytes()
    m=verify(content=True)
    assert m.version=='sealed-manifest-v2' and m.acceptance=='not_assessed'
    assert m.parent_manifest_sha256==hashlib.sha256((old/'manifest.json').read_bytes()).hexdigest()
    a=json.loads((old/'cases.json').read_text())['cases'];b=json.loads((BUNDLE/'cases.json').read_text())['cases']
    for before,after in zip(a,b):
        if before['id']=='s03':
            assert '你没有说' not in after['candidate'] and '按你刚才的纠正' in after['candidate']
        else:assert before==after
    # The old policy binding may only be replayed under its original code baseline.
    with pytest.raises(ValueError,match='policy drift'):verify(old,content=True)

@pytest.mark.parametrize('change',[
    lambda d:d.update(parent_manifest_sha256=None),
    lambda d:d.update(parent_manifest_sha256='0'*64),
    lambda d:d.update(revision_reason=None),
])
def test_v2_requires_valid_frozen_parent_and_reason(tmp_path,change):
    import shutil
    bundle=tmp_path/'v2';shutil.copytree(BUNDLE,bundle)
    path=bundle/'manifest.json';data=json.loads(path.read_text());change(data);path.write_text(json.dumps(data))
    with pytest.raises(ValueError):verify(bundle,content=True)


def test_cross_version_artifacts_cannot_be_mixed(tmp_path):
    import shutil
    bundle=tmp_path/'v2';shutil.copytree(BUNDLE,bundle)
    path=bundle/'cases.json';data=json.loads(path.read_text());data['version']='sealed-candidate-v1';path.write_text(json.dumps(data))
    manifest=bundle/'manifest.json';m=json.loads(manifest.read_text());m['artifacts']['cases.json']=hashlib.sha256(path.read_bytes()).hexdigest();manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='schema versions'):verify(bundle,content=True)


def test_real_review_timeout_cancels_once_and_returns_busy(tmp_path):
    cancelled=[]
    async def slow(*args):
        try:await asyncio.sleep(60)
        finally:cancelled.append(True)
    judge=SimpleNamespace(review=AsyncMock(side_effect=slow))
    provider=SimpleNamespace(generate=AsyncMock(return_value=GOOD))
    c,h=client(tmp_path,provider,judge,semantic_review_timeout_seconds=.1)
    r=c.post('/v1/chat',headers=h,json={'message':'你好'})
    assert r.status_code==503 and r.json()['detail']==BUSY_MESSAGE
    assert cancelled==[True] and judge.review.await_count==1 and provider.generate.await_count==1
    assert c.get('/v1/session').json()['messages']==[]
