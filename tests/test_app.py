from types import SimpleNamespace
from unittest.mock import AsyncMock
import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.dialogue import FALLBACK, OpenAIProvider, ProviderFailure
from app.main import create_app


def settings(**kwargs):
    return Settings(_env_file=None, chat_provider='mock', **kwargs)


def connected(provider=None):
    client = TestClient(create_app(settings(), provider))
    data = client.get('/v1/session').json()
    return client, {'x-csrf-token': data['csrf_token']}


def test_page_config_and_secret_not_exposed():
    client = TestClient(create_app(Settings(_env_file=None, openai_api_key='test-private-value')))
    assert client.get('/').status_code == 200
    response = client.get('/v1/session')
    assert response.json()['configured']
    assert 'test-private-value' not in response.text
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'frame-ancestors' in response.headers['content-security-policy']
    assert client.get('/.env').status_code == 404
    assert client.get('/static/../../.env').status_code == 404


def test_chat_history_refresh_and_reset():
    client, headers = connected()
    first = client.post('/v1/chat', headers=headers, json={'message': '我下周面试'})
    assert first.status_code == 200
    assert first.json()['request_id']
    assert first.json()['request_id'] == first.headers['x-request-id']
    reply = client.post('/v1/chat', headers=headers, json={'message': '还记得刚才说了什么吗'}).json()['reply']
    assert '我下周面试' in reply
    assert len(client.get('/v1/session').json()['messages']) == 4
    assert client.delete('/v1/session', headers=headers).status_code == 200
    assert client.get('/v1/session').json()['messages'] == []


def test_session_isolation_and_csrf():
    a, headers = connected()
    b = TestClient(a.app)
    bdata = b.get('/v1/session').json()
    a.post('/v1/chat', headers=headers, json={'message': '私人测试事件'})
    assert b.get('/v1/session').json()['messages'] == []
    assert b.post('/v1/chat', headers=headers, json={'message': '你好'}).status_code == 403
    assert b.post('/v1/chat', headers={'x-csrf-token': bdata['csrf_token'], 'origin':'https://evil.example'}, json={'message':'你好'}).status_code == 403
    assert TestClient(a.app).post('/v1/chat', json={'message':'你好'}).status_code == 401


@pytest.mark.parametrize('message', ['', '  ', 'x' * 2001])
def test_validation(message):
    client, headers = connected()
    assert client.post('/v1/chat', headers=headers, json={'message':message}).status_code == 422


def test_body_limit_and_host():
    client, headers = connected()
    assert client.post('/v1/chat', headers=headers, json={'message':'a'*20000}).status_code == 413
    assert client.get('/', headers={'host':'evil.example'}).status_code == 400


def test_missing_key_is_explicit_not_mock():
    client = TestClient(create_app(Settings(_env_file=None, openai_api_key='')))
    data = client.get('/v1/session').json()
    assert not data['configured']
    result = client.post('/v1/chat', headers={'x-csrf-token':data['csrf_token']}, json={'message':'你好'})
    assert result.status_code == 503
    assert result.json()['code'] == 'missing_api_key'
    assert client.get('/v1/session').json()['messages'] == []


def test_guard_rewrites_then_falls_back():
    provider = SimpleNamespace(generate=AsyncMock(return_value='我今年19岁，我是医生。'))
    client, headers = connected(provider)
    data = client.post('/v1/chat', headers=headers, json={'message':'你是谁'}).json()
    assert data['reply'] == FALLBACK
    assert data['guarded']
    assert provider.generate.await_count == 2


def test_guard_accepts_corrected_reply():
    provider = SimpleNamespace(generate=AsyncMock(side_effect=['我今年21岁。', '我今年28岁，在栖川开旧书店。']))
    client, headers = connected(provider)
    assert '28岁' in client.post('/v1/chat', headers=headers, json={'message':'年龄'}).json()['reply']


def test_provider_error_preserves_history():
    provider = SimpleNamespace(generate=AsyncMock(side_effect=ProviderFailure('timeout','测试超时',504)))
    client, headers = connected(provider)
    assert client.post('/v1/chat', headers=headers, json={'message':'你好'}).status_code == 504
    assert client.get('/v1/session').json()['messages'] == []


def test_expired_session_and_capacity():
    client, headers = connected()
    session = next(iter(client.app.state.sessions.values()))
    session.touched -= 99999
    assert client.post('/v1/chat', headers=headers, json={'message':'你好'}).status_code == 401
    assert client.get('/v1/session').status_code == 200
    app = create_app(settings(max_sessions=1))
    assert TestClient(app).get('/v1/session').status_code == 200
    assert TestClient(app).get('/v1/session').status_code == 503


def test_busy_prevents_chat_and_reset():
    client, headers = connected()
    session = next(iter(client.app.state.sessions.values()))
    asyncio.run(session.lock.acquire())
    try:
        assert client.post('/v1/chat', headers=headers, json={'message':'你好'}).status_code == 409
        assert client.delete('/v1/session', headers=headers).status_code == 409
    finally:
        session.lock.release()


def test_history_bounded():
    client, headers = connected()
    for _ in range(15):
        assert client.post('/v1/chat', headers=headers, json={'message':'你好'}).status_code == 200
    assert len(client.get('/v1/session').json()['messages']) == 24


def test_openai_request_contract(monkeypatch):
    generate = AsyncMock(return_value=SimpleNamespace(output_text='我在听。', status='completed'))
    class Client:
        def __init__(self, **kwargs):
            assert kwargs['max_retries'] == 0
            self.responses = SimpleNamespace(create=generate)
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    monkeypatch.setattr('openai.AsyncOpenAI', Client)
    provider = OpenAIProvider(Settings(_env_file=None, openai_api_key='test-local'))
    result = asyncio.run(provider.generate([{'role':'user','content':'你好'}], '角色设定'))
    assert result == '我在听。'
    kwargs = generate.call_args.kwargs
    assert kwargs['store'] is False
    assert kwargs['instructions'] == '角色设定'
    assert kwargs['input'][0]['role'] == 'user'


SCENARIOS = json.loads((Path(__file__).parent / 'scenarios.json').read_text())


@pytest.mark.parametrize('case', SCENARIOS, ids=lambda c:c['id'])
def test_mock_synthetic_scenarios(case):
    client, headers = connected()
    result = client.post('/v1/chat', headers=headers, json={'message':case['message']})
    assert result.status_code == 200
    assert case['expected_fragment'] in result.json()['reply']


def test_retrieval_baseline_sources():
    from app.dialogue import retrieve_canon, instructions
    selected = retrieve_canon('你的书店是继承的吗？')
    assert 'C03' in [c['id'] for c in selected]
    assert 'C03' in instructions('rag', '书店是继承的吗')
    assert '正史证据' not in instructions('direct')


@pytest.mark.parametrize('kind,status,code', [('auth',503,'invalid_api_key'),('rate',429,'rate_limit'),('timeout',504,'timeout'),('connection',502,'connection'),('upstream',502,'upstream_error'),('empty',502,'empty_response')])
def test_sdk_failures_are_sanitized(monkeypatch, kind, status, code):
    import openai
    import httpx
    req = httpx.Request('POST', 'https://api.openai.com/v1/responses')
    response = httpx.Response(500, request=req)
    errors = {
        'auth': openai.AuthenticationError('private-upstream-message', response=response, body=None),
        'rate': openai.RateLimitError('private-upstream-message', response=response, body=None),
        'timeout': openai.APITimeoutError(request=req),
        'connection': openai.APIConnectionError(request=req),
        'upstream': openai.APIStatusError('private-upstream-message', response=response, body=None),
    }
    generate = AsyncMock(return_value=SimpleNamespace(output_text='', status='incomplete'))
    if kind != 'empty': generate.side_effect = errors[kind]
    class Client:
        def __init__(self, **kwargs): self.responses = SimpleNamespace(create=generate)
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    monkeypatch.setattr('openai.AsyncOpenAI', Client)
    client = TestClient(create_app(Settings(_env_file=None, openai_api_key='test-private-value')))
    csrf = client.get('/v1/session').json()['csrf_token']
    result = client.post('/v1/chat', headers={'x-csrf-token':csrf}, json={'message':'你好'})
    assert result.status_code == status
    assert result.json()['code'] == code
    assert 'private-upstream-message' not in result.text
    assert 'test-private-value' not in result.text
