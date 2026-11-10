"""Explicit companion defaults; no credentials, network, or real player history."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app import companion
from app.dialogue import instructions
from app.memory import memory_prompt
from app.reply_pipeline import generate_checked
from app.semantic_review import IndexedReview


def client(tmp_path, text, *, mode='companion', judge=None):
    provider = SimpleNamespace(generate=AsyncMock(return_value=text))
    judge = judge or SimpleNamespace(review=AsyncMock(side_effect=TimeoutError()))
    app = create_app(Settings(_env_file=None, chat_provider='mock', dialogue_mode=mode,
        memory_database_url='sqlite:///'+str(tmp_path/'synthetic.sqlite3')), provider, semantic_judge=judge)
    c = TestClient(app)
    h = {'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    return c, h, provider, judge


@pytest.mark.parametrize('text', [
    '你好呀，我在呢。今天过得怎么样？',
    '来啦。我把手里的书放下，听你说。',
    '窗边的暖灯亮着，书页轻轻响了一声。你慢慢说。',
    '辛苦啦，先歇一会儿也好。不急着把所有事情都做好。',
])
def test_greeting_and_atmosphere_do_not_depend_on_second_model(tmp_path, text):
    c, h, provider, judge = client(tmp_path, text)
    c.app.state.memory_store.retrieve = Mock(side_effect=AssertionError('must not read memory'))
    r = c.post('/v1/chat', headers=h, json={'message':'你好'})
    assert r.status_code == 200 and r.json()['reply'] == text
    assert r.json()['semantic_review'] == {'status':'skipped', 'calls':0}
    provider.generate.assert_awaited_once(); judge.review.assert_not_awaited()
    assert c.get('/v1/session').json()['messages'][-1]['content'] == text
    assert c.get('/v1/memories').json()['items'] == []
    assert '先接住这句话' in provider.generate.call_args.args[1]


def test_reproduces_old_hello_failure_without_api(tmp_path):
    c, h, provider, judge = client(tmp_path, '你好呀，我在呢。今天过得怎么样？', mode='audit')
    r = c.post('/v1/chat', headers=h, json={'message':'你好'})
    assert r.status_code == 503 and r.json()['code'] == 'review_busy'
    assert provider.generate.await_count == judge.review.await_count == 1
    assert c.get('/v1/session').json()['messages'] == []


@pytest.mark.parametrize('text', [
    '我记得你的猫叫合成豆沙。', '你今天过来，是想找书吗？',
    '我父亲把书店留给了我。', '我已经帮你付清预约费了。',
])
def test_important_claim_review_failure_does_not_publish_draft(tmp_path, text):
    c, h, _, judge = client(tmp_path, text)
    r = c.post('/v1/chat', headers=h, json={'message':'你好'})
    assert r.status_code == 503 and judge.review.await_count == 1
    assert c.get('/v1/session').json()['messages'] == []


def test_confirmed_memory_is_still_reviewed_and_revocable(tmp_path):
    c, h, _, judge = client(tmp_path, '我记得你叫合成松露。')
    assert c.patch('/v1/settings', headers=h, json={'memory_enabled':True}).status_code == 200
    item = c.post('/v1/memories', headers=h, json={'fact':'我叫合成松露'}).json()['item']
    item = c.patch('/v1/memories/'+item['id'], headers=h,
        json={'version':item['version'], 'confirm':True}).json()['item']
    assert c.post('/v1/chat', headers=h, json={'message':'我的名字是什么？'}).status_code == 503
    evidence = judge.review.call_args.args[2]
    assert any(e['id'] == 'memory_'+item['id'] for e in evidence)
    assert c.delete('/v1/memories/'+item['id'], headers=h, params={'version':item['version']}).status_code == 200
    assert c.get('/v1/memories').json()['items'] == []


def test_hard_canon_rewrites_even_when_judge_mistakenly_accepts():
    text = '我今年19岁。'
    judge = SimpleNamespace(review=AsyncMock(return_value={
        'decision':'accept', 'confidence':.95, 'role_issues':[],
        'segments':[{'text':text, 'kind':'assertion', 'verdict':'supported',
                     'evidence_ids':['C01'], 'reason':'evidence_supports'}]}))
    provider = SimpleNamespace(generate=AsyncMock(return_value=text))
    reply, guarded, _ = asyncio.run(generate_checked(provider, [], companion.instructions(), '你好',
        [], None, None, {}, judge=judge, companion=True))
    assert reply == companion.FALLBACK and guarded
    assert provider.generate.await_count == judge.review.await_count == 2
    rewrite = provider.generate.call_args.args[1]
    assert '只去掉或纠正那一处' in rewrite


def test_compact_prompt_and_no_project_route(tmp_path):
    c, _, _, _ = client(tmp_path, '你好呀。')
    assert c.get('/v1/project').status_code == 404
    assert len(companion.instructions()) < len(instructions())
    memory = [{'id':'m', 'fact':'我住在合成松露市', 'event_date':None}]
    assert len(companion.memory_context(memory, '你好')) < len(memory_prompt(memory))
    assert '合成松露市' in companion.memory_context(memory, '你好')


def test_compact_review_prompt_is_selected_without_changing_audit(monkeypatch):
    from app.semantic_review import ModelAnalysisProvider
    seen = []
    async def parse(self, schema, prompt, data, timeout, tokens):
        seen.append(prompt)
    monkeypatch.setattr(ModelAnalysisProvider, 'parse', parse)
    provider = companion.CompanionAnalysisProvider(SimpleNamespace())
    asyncio.run(provider.parse(IndexedReview, 'old prompt', {}, 8, 700))
    assert seen == [companion.REVIEW_PROMPT]


def test_production_default_is_companion_without_test_audit_override(monkeypatch):
    monkeypatch.delenv('DIALOGUE_MODE', raising=False)
    assert Settings(_env_file=None).dialogue_mode == 'companion'


@pytest.mark.parametrize('memories,weather,mood', [
    ([{'id':'m'}], None, None),
    ([], {'status':'ok', 'temperature_c':6}, None),
    ([], None, {'assessment':{'labels':['sadness']}}),
])
def test_memory_and_real_tool_context_are_not_treated_as_plain_greeting(memories, weather, mood):
    assert companion.review_required('你好', '我在呢。', memories, weather, mood)


def test_confirmed_memory_can_pass_review_and_survive_new_session(tmp_path):
    judge = SimpleNamespace(review=AsyncMock())
    c, h, _, judge = client(tmp_path, '我记得你叫合成松露。', judge=judge)
    c.patch('/v1/settings', headers=h, json={'memory_enabled':True})
    item = c.post('/v1/memories', headers=h, json={'fact':'我叫合成松露'}).json()['item']
    c.patch('/v1/memories/'+item['id'], headers=h, json={'version':item['version'], 'confirm':True})
    async def accept(reply, history, evidence):
        assert any(e['id'] == 'memory_'+item['id'] for e in evidence)
        return {'decision':'accept', 'confidence':.95, 'role_issues':[], 'segments':[
            {'text':reply, 'kind':'assertion', 'verdict':'supported',
             'evidence_ids':['memory_'+item['id']], 'reason':'evidence_supports'}]}
    judge.review.side_effect = accept
    for _ in range(2):
        c.delete('/v1/session', headers=h)
        r = c.post('/v1/chat', headers=h, json={'message':'我的名字是什么？'})
        assert r.status_code == 200 and r.json()['retrieved_memory_ids'] == [item['id']]
        assert r.json()['reply'] == '我记得你叫合成松露。'
    assert judge.review.await_count == 2


def test_consent_epoch_still_revokes_an_unreviewed_greeting(tmp_path):
    c, h, provider, judge = client(tmp_path, '我在呢。')
    uid = next(iter(c.app.state.sessions.values())).user_id
    async def generate(*args):
        c.app.state.memory_store.invalidate(uid)
        return '我在呢。'
    provider.generate.side_effect = generate
    r = c.post('/v1/chat', headers=h, json={'message':'你好'})
    assert r.status_code == 409 and r.json()['code'] == 'memory_changed'
    assert c.get('/v1/session').json()['messages'] == []
    judge.review.assert_not_awaited()


def test_smalltalk_keeps_multi_turn_context_without_repeated_audits(tmp_path):
    c, h, provider, judge = client(tmp_path, '嗯，我在呢。')
    for message in ('你好', '只是想和你聊一会儿'):
        assert c.post('/v1/chat', headers=h, json={'message':message}).status_code == 200
    assert provider.generate.await_count == 2
    assert len(provider.generate.call_args.args[0]) == 3
    assert len(c.get('/v1/session').json()['messages']) == 4
    judge.review.assert_not_awaited()


@pytest.mark.parametrize('query,text', [
    ('我叫什么名字？', '你叫合成松露。'),
    ('我住哪儿？', '你住在合成松露市。'),
])
def test_missing_or_disabled_memory_does_not_license_personal_fact_guess(tmp_path, query, text):
    c, h, _, judge = client(tmp_path, text)
    c.app.state.memory_store.retrieve = Mock(side_effect=AssertionError('memory is disabled'))
    r = c.post('/v1/chat', headers=h, json={'message':query})
    assert r.status_code == 503 and judge.review.await_count == 1
    assert c.get('/v1/session').json()['messages'] == []
