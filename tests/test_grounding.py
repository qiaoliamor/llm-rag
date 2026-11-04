from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.dialogue import FALLBACK
from app.main import create_app
from app.grounding import (GROUNDING_RULES,grounding_prompt,grounding_conflicts,
                           protected_places,place_conflicts,scene_conflicts)


@pytest.mark.parametrize('reply',[
    '今天店里比平时安静一些。','店内没什么人，刚收到的旧书你可以看看。',
    '书店今天很热闹。','这里挤满了客人。','最近进了一批旧书。',
    '我刚泡好茶。','刚收到几本新书。','今天书店没有客人。',
    '我不知道，但是今天店里很安静。',
    '新书倒没有刚收到。','店里今天具体是什么样的，我还真没留意。',
    '今天店里翻到了一本讲动物行为的旧书。','刚收到了一箱别人转手的老旧杂志。',
])
def test_unsupported_dynamic_scene(reply):
    assert scene_conflicts(reply)


@pytest.mark.parametrize('reply',[
    '我在栖川经营一家旧书店。','我喜欢修补旧书。','想来坐坐的话，随时可以。',
    '我记得你的猫叫合成松饼。它最近还好吗？',
    '我不知道店里今天是否安静。','如果店里安静，我们可以聊聊书。',
    '你可以先喝点水，慢慢说。','你的店里今天很安静。','你刚收到几本新书。',
])
def test_canon_invitation_and_unknown_are_allowed(reply):
    assert not scene_conflicts(reply)


@pytest.mark.parametrize('fact',[
    '我住在合成青禾市','我目前住在新海滨县','我的家位于北星河区',
])
def test_places_are_derived_from_data(fact):
    names=protected_places([{'fact':fact}])
    assert len(names)==1
    name=names[0]
    assert not place_conflicts('我记得你住在'+name+'。',names)
    assert place_conflicts('我记得你住在'+name[1:]+'。',names)
    assert place_conflicts('我记得你住在'+name[:-1]+'。',names)
    assert place_conflicts('我记得你住在'+name[1:-1]+'。',names)
    assert not place_conflicts('那里最近怎么样？',names)
    assert not place_conflicts('具体地点我无法确定。',names)


def test_multiple_places_current_assertion_and_no_question_evidence():
    names=protected_places([{'fact':'我住在合成青禾市'},{'fact':'我住在青禾市'}])
    assert not place_conflicts('青禾市和合成青禾市是不同写法。',names)
    assert protected_places([], '我住在合成青禾市')==['合成青禾市']
    assert protected_places([], '我住在合成青禾市，对吗？')==[]
    assert protected_places([{'fact':'如果我住在合成青禾市'}])==[]
    assert protected_places([{'fact':'我不住在合成青禾市'}])==[]
    assert protected_places([{'fact':'我的猫叫松饼'}])==[]


def test_prompt_without_memory_still_prohibits_scene_fabrication():
    assert GROUNDING_RULES in grounding_prompt([])
    assert '合成青禾市' in grounding_prompt([{'fact':'我住在合成青禾市'}])
    assert grounding_conflicts('今天店里很安静。',[])


@pytest.mark.parametrize('reply',['今天店里很安静。','我记得你住在青禾市。',
                                  '新书倒没有刚收到。','店里今天具体是什么样的，我还真没留意。'])
@pytest.mark.parametrize('retry_ok',[True,False])
def test_chat_rewrites_and_falls_back_without_saving_invalid_reply(tmp_path,reply,retry_ok):
    second='我在听，你想聊聊那里吗？' if retry_ok else reply
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[reply,second]))
    app=create_app(Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'guard.db')),provider)
    with TestClient(app) as client:
        headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
        data=client.post('/v1/chat',headers=headers,json={'message':'我住在合成青禾市'}).json()
        assert data['guarded'] and data['reply']==(second if retry_ok else FALLBACK)
        assert provider.generate.await_count==2
        assert client.get('/v1/session').json()['messages'][-1]['content']==data['reply']
        assert '不缩写地名' in provider.generate.await_args.args[1]


def test_scene_rewrite_failure_never_saves_invalid_turn(tmp_path):
    from app.dialogue import ProviderFailure
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[
        '今天店里很安静。',ProviderFailure('rate_limit','稍后重试',429)]))
    app=create_app(Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'error.db')),provider)
    with TestClient(app) as client:
        headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
        result=client.post('/v1/chat',headers=headers,json={'message':'你好'})
        assert result.status_code==429
        assert client.get('/v1/session').json()['messages']==[]
        assert provider.generate.await_count==2


def test_live_prompts_only_differ_in_grounding_and_bounds_prevent_calls(monkeypatch):
    import asyncio
    from scripts import evaluate_grounding as evaluation
    for case in evaluation.CASES:
        assert evaluation.prompt_for(case,True)==evaluation.prompt_for(case,False)+grounding_prompt(evaluation.evidence_for(case),case['query'])
    monkeypatch.setattr(evaluation,'Settings',lambda: (_ for _ in ()).throw(AssertionError('must validate first')))
    for kwargs in ({'repeats':3},{'interval':-1},{'interval':float('nan')}):
        with pytest.raises(ValueError):asyncio.run(evaluation.run(**kwargs))


def test_live_fake_provider_is_bounded_and_reports_redacted_failure(monkeypatch):
    import asyncio
    from scripts import evaluate_grounding as evaluation
    from app.dialogue import ProviderFailure
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[
        '今天店里很安静。',ProviderFailure('rate_limit','do not expose raw error',429),
        '我记得你住在合成青禾市。','我记得你住在青禾市。','店里今天很热闹。','我无法确定。']))
    monkeypatch.setattr(evaluation,'Settings',lambda:SimpleNamespace(chat_provider='gemini',configured=True,selected_model='fake'))
    monkeypatch.setattr(evaluation,'build_provider',lambda settings:provider)
    report=asyncio.run(evaluation.run(repeats=1,interval=0))
    assert report['api_calls']==provider.generate.await_count==6
    assert report['trials'][1]['status']=='error' and report['trials'][1]['code']=='rate_limit'
    assert 'do not expose' not in str(report)
    assert report['trials'][3]['place_guard']
    assert report['trials'][0]['scene_guard']



def test_disposable_pipeline_uses_existing_guard_and_at_most_two_calls(monkeypatch):
    from scripts import evaluate_grounding as evaluation
    provider=SimpleNamespace(generate=AsyncMock(return_value='店里今天具体是什么情况，我没有留意。'))
    monkeypatch.setattr(evaluation,'Settings',lambda:Settings(_env_file=None,chat_provider='gemini',gemini_api_key='test-placeholder'))
    monkeypatch.setattr(evaluation,'build_provider',lambda settings:provider)
    report=evaluation.run_pipeline()
    assert report['status_code']==200 and report['guarded']
    assert report['api_calls']==provider.generate.await_count==2
    assert report['reply']==FALLBACK
    assert 'test-placeholder' not in str(report)
