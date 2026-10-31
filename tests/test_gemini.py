"""Exercise the real SDK against an in-memory HTTP transport; no API key/network."""
import json
import subprocess

import httpx2
import openai
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, ROOT
from app.dialogue import GeminiProvider, OpenAIProvider, MockProvider, build_provider, instructions
from app.main import create_app


def config(**overrides):
    return Settings(_env_file=None, chat_provider='gemini', gemini_api_key='test-gemini-private', **overrides)


def install_transport(monkeypatch, handler):
    real_client = openai.AsyncOpenAI
    def factory(**kwargs):
        return real_client(**kwargs, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    monkeypatch.setattr(openai, 'AsyncOpenAI', factory)


def completion(content='我是沈砚，今年28岁。', finish='stop', refusal=None):
    return {'id':'test-completion', 'object':'chat.completion', 'created':0,
            'model':'gemini-3.5-flash-lite',
            'choices':[{'index':0, 'finish_reason':finish,
                        'message':{'role':'assistant', 'content':content, 'refusal':refusal}}]}


def chat(client, text='你好'):
    session = client.get('/v1/session').json()
    return client.post('/v1/chat', headers={'x-csrf-token':session['csrf_token']}, json={'message':text})


def test_provider_selection_and_defaults():
    assert Settings(_env_file=None).chat_provider == 'gemini'
    assert isinstance(build_provider(config()), GeminiProvider)
    assert isinstance(build_provider(Settings(_env_file=None, chat_provider='openai')), OpenAIProvider)
    assert isinstance(build_provider(Settings(_env_file=None, chat_provider='mock')), MockProvider)


def test_real_sdk_wire_and_multiturn(monkeypatch):
    requests = []
    def handler(request):
        assert str(request.url) == 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
        assert request.headers['authorization'] == 'Bearer test-gemini-private'
        payload = json.loads(request.content)
        assert payload['model'] == 'gemini-3.5-flash-lite'
        assert payload['max_tokens'] == 500
        assert payload['messages'][0] == {'role':'system', 'content':instructions()}
        assert 'store' not in payload and 'instructions' not in payload
        requests.append(payload)
        return httpx2.Response(200, json=completion())
    install_transport(monkeypatch, handler)
    client = TestClient(create_app(config()))
    assert chat(client, '我明天有面试').status_code == 200
    assert chat(client, '你记得我刚说什么吗').status_code == 200
    assert [m['role'] for m in requests[1]['messages']] == ['system','user','assistant','user']
    assert requests[1]['messages'][1]['content'] == '我明天有面试'
    session = client.get('/v1/session').json()
    assert session['provider'] == 'gemini'
    assert session['model'] == 'gemini-3.5-flash-lite'
    assert session['configured']
    assert 'test-gemini-private' not in json.dumps(session)


@pytest.mark.parametrize('status,expected,code', [(400,503,'invalid_config'), (401,503,'invalid_api_key'),
    (403,503,'permission_denied'), (404,502,'upstream_error'), (429,429,'rate_limit'), (500,502,'upstream_error')])
def test_api_errors_no_retry_no_secret(monkeypatch, status, expected, code):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx2.Response(status, json={'error':{'message':'private-upstream-error test-gemini-private', 'code':status}})
    install_transport(monkeypatch, handler)
    client = TestClient(create_app(config()))
    response = chat(client)
    assert response.status_code == expected
    assert response.json()['code'] == code
    assert 'test-gemini-private' not in response.text and 'private-upstream-error' not in response.text
    assert len(calls) == 1
    assert client.get('/v1/session').json()['messages'] == []


@pytest.mark.parametrize('error,code,status', [(httpx2.ReadTimeout,'timeout',504),(httpx2.ConnectError,'connection',502)])
def test_transport_failure(monkeypatch, error, code, status):
    def handler(request):
        raise error('private-network-error', request=request)
    install_transport(monkeypatch, handler)
    response = chat(TestClient(create_app(config())))
    assert response.status_code == status
    assert response.json()['code'] == code
    assert 'private-network-error' not in response.text
    assert 'OpenAI' not in response.text


@pytest.mark.parametrize('payload,code,status', [
    ({'id':'empty','object':'chat.completion','created':0,'model':'gemini-3.5-flash-lite','choices':[]},'empty_response',502),
    (completion(''),'empty_response',502),
    (completion('   '),'empty_response',502),
    (completion(None),'empty_response',502),
    (completion('截断文本','length'),'empty_response',502),
    (completion(None,'content_filter'),'content_blocked',422),
    (completion(None,refusal='blocked'),'content_blocked',422),
])
def test_empty_truncated_and_filtered(monkeypatch,payload,code,status):
    install_transport(monkeypatch, lambda request:httpx2.Response(200,json=payload))
    client = TestClient(create_app(config()))
    response = chat(client)
    assert response.status_code == status
    assert response.json()['code'] == code
    assert client.get('/v1/session').json()['messages'] == []


def test_gemini_missing_key_does_not_use_openai_key(monkeypatch):
    def unexpected(**kwargs):
        pytest.fail('Missing Gemini key must never create an API client')
    monkeypatch.setattr(openai,'AsyncOpenAI',unexpected)
    client = TestClient(create_app(
        Settings(_env_file=None,chat_provider='gemini',gemini_api_key='',openai_api_key='other-private-key')))
    data = client.get('/v1/session').json()
    assert not data['configured'] and data['api_key_env'] == 'GEMINI_API_KEY'
    response = chat(client)
    assert response.status_code == 503
    assert 'GEMINI_API_KEY' in response.json()['detail']
    assert 'other-private-key' not in response.text


def test_gemini_guarded_rewrite(monkeypatch):
    count = 0
    def handler(request):
        nonlocal count
        count += 1
        return httpx2.Response(200,json=completion('我今年19岁。' if count == 1 else '我今年28岁。'))
    install_transport(monkeypatch,handler)
    response = chat(TestClient(create_app(config())))
    assert response.json()['guarded']
    assert response.json()['reply'] == '我今年28岁。'
    assert count == 2


def test_live_evaluator_requires_selected_key():
    import os
    env = {**os.environ,'CHAT_PROVIDER':'gemini','GEMINI_API_KEY':'','OPENAI_API_KEY':'unused-private-key'}
    result = subprocess.run([str(ROOT / '.venv/bin/python'),'scripts/evaluate.py','--live','--limit','1'],
                            cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode != 0
    assert 'GEMINI_API_KEY' in result.stderr
    assert 'unused-private-key' not in result.stderr
