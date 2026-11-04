from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.dialogue import FALLBACK
from app.main import create_app
from app.memory import memory_prompt
from app.memory_source import source_time_conflicts


@pytest.mark.parametrize('reply', [
    '你刚才告诉我，你叫合成小岚。', '我记得你刚才告诉过我，你叫合成小岚。',
    '我刚听你说起，你叫合成小岚。', '我刚才听到的名字是合成小岚。',
    '你今天告诉我，你养了一只猫。', '你这轮提过，你住在青禾市。',
    '你本次会话跟我说过，你叫小岚。', '刚才你告诉我，你叫小岚。', '你刚告诉我，你叫小岚。',
])
def test_unsupported_source_time(reply):
    assert source_time_conflicts(reply,[{'role':'user','content':'你还记得我的名字吗？'}])


@pytest.mark.parametrize('reply', ['我记得你叫合成小岚。', '我记得你提过养猫。',
                                   '你前面说过你喜欢书。', '刚才下雨了，出门带把伞。'])
def test_no_source_time_claim(reply):
    assert not source_time_conflicts(reply,[])


def test_current_assertion_only_not_history_or_question():
    reply='你刚才告诉我，你叫小岚。'
    assert not source_time_conflicts(reply,[{'role':'user','content':'我叫小岚。'}])
    for history in [
        [{'role':'user','content':'我叫小岚。'},{'role':'user','content':'我的名字是什么？'}],
        [{'role':'assistant','content':'我叫小岚。'}],
        [{'role':'user','content':'我叫小岚，对吗？'}],
        [{'role':'user','content':'如果我叫小岚。'}],
        [{'role':'user','content':'我叫红豆。'}],
    ]: assert source_time_conflicts(reply,history)
    assert source_time_conflicts('你今天告诉我，你叫小岚。',[{'role':'user','content':'我叫小岚。'}])


def test_prompt_keeps_fact_and_date_without_telling_time():
    data=[{'id':'synthetic','fact':'我今天有面试','event_date':'2026-11-04'}]
    prompt=memory_prompt(data)
    assert '不是讲述、创建、确认或检索时间' in prompt
    assert '我今天有面试' in prompt and '2026-11-04' in prompt
    assert 'memory-source-time-v1' not in memory_prompt(data,source_time=False)
    assert memory_prompt([])==''


@pytest.mark.parametrize('second', ['我记得你叫小岚。','你刚才告诉我，你叫小岚。'])
def test_chat_regenerates_once_and_only_saves_valid_answer(second,tmp_path):
    provider=SimpleNamespace(generate=AsyncMock(side_effect=['你刚才告诉我，你叫小岚。',second]))
    app=create_app(Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///' + str(tmp_path/'source.sqlite3')),provider)
    with TestClient(app) as client:
        session=client.get('/v1/session').json()
        result=client.post('/v1/chat',headers={'x-csrf-token':session['csrf_token']},json={'message':'我的名字是什么？'})
        assert result.status_code==200
        reply=second if second.startswith('我记得') else FALLBACK
        assert result.json()['reply']==reply and result.json()['guarded']
        assert provider.generate.await_count==2
        assert client.get('/v1/session').json()['messages'][-1]['content']==reply
        assert '长期记忆不证明' in provider.generate.await_args_list[1].args[1]


@pytest.mark.parametrize('reply', [
    '我其实记不太清了。', '我们见面的时间不算太久，我也没特意去记那个时刻。',
    '是上个月的二十号吧？那会儿正好聊到这事。',
])
def test_unknown_telling_date_is_not_event_date_or_forgotten_scene(reply):
    assert source_time_conflicts(reply,[{'role':'user','content':'我什么时候告诉你住哪儿的？'}])


def test_rewrite_error_does_not_save_unsupported_answer(tmp_path):
    from app.dialogue import ProviderFailure
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[
        '你刚才告诉我，你叫小岚。',ProviderFailure('rate_limit','稍后重试',429)]))
    app=create_app(Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'failure.sqlite3')),provider)
    with TestClient(app) as client:
        headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
        result=client.post('/v1/chat',headers=headers,json={'message':'我的名字是什么？'})
        assert result.status_code==429
        assert client.get('/v1/session').json()['messages']==[]
        assert provider.generate.await_count==2


def test_live_pair_changes_only_source_rules_and_uses_synthetic_cases():
    from scripts.evaluate_memory_source import CASES,prompt_for
    from app.memory_source import SOURCE_TIME_RULES
    for case in CASES:
        assert prompt_for(case,True).replace(SOURCE_TIME_RULES,'')==prompt_for(case,False)
        assert case['fact'] in prompt_for(case,True)
        assert '合成' in case['fact']
