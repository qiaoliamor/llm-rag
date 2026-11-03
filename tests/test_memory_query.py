"""Question/evidence compatibility and routing regressions using synthetic facts."""
import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.memory import RetrievalPolicy,embed,rank_memories
from app.memory_query import compatible,evidence_need
from app.retrieval_evaluation import REGRESSION_DATASET,compare_prompts,evaluate_retrieval


@pytest.mark.parametrize('query,fact,expected',[
    ('我的名字是什么','我叫合成阿澄',True),
    ('我的名字是什么','我的猫咪叫合成阿澄',False),
    ('我的名字是什么','我的朋友叫合成阿澄',False),
    ('我的名字是什么','我叫朋友来帮忙',False),
    ('我名字是什么','我叫“小岚”',True),
    ('我的护照号码是什么','我叫合成甲',False),
    ('我的护照号码是什么','我的护照号码是SYNTHETIC-PASS',True),
    ('我的护照号码是什么','我的朋友的护照号码是FRIEND-ONLY',False),
    ('我的护照号码是什么','我知道朋友的护照号码是FRIEND-ONLY',False),
    ('我的护照号码是什么','我的护照号码不是SYNTHETIC-PASS',False),
    ('我的手机号是什么','我的手机号是SYNTHETIC-PHONE',True),
    ('我的身份证号是什么','我的护照号码是SYNTHETIC-PASS',False),
    ('我小时候住哪','我现在住在合成临川',False),
    ('我小时候住哪','我小时候住在合成旧镇',True),
    ('我小时候和父母住哪','我小时候住在合成旧镇',True),
    ('我小时候住哪','我小时候和父母住在合成旧镇',True),
    ('我小时候住哪','我的朋友小时候住在合成旧镇',False),
    ('我现在住哪','我以前住在合成旧镇',False),
    ('我以前住哪','我现在住在合成临川',False),
    ('我以前住哪','我以前住在合成旧镇',True),
    ('我住哪里','我不住在合成旧镇',False),
    ('我住哪里','我不是住在合成旧镇',False),
    ('我住哪里','我知道朋友住在合成旧镇',False),
    ('我的名字是什么','我以前叫合成旧名',False),
    ('我以前叫什么名字','我以前叫合成旧名',True),
    ('我的妈妈叫什么名字','我的朋友叫合成小岚',False),
    ('我的妈妈叫什么名字','我的妈妈叫合成小岚',True),
    ('我的妈妈叫什么名字，不是朋友的名字','我的朋友叫合成小岚',False),
    ('我的妈妈叫什么名字，不是朋友的名字','我的妈妈叫合成小岚',True),
    ('我的朋友叫什么名字','我的朋友说我叫合成小岚',False),
    ('我养的猫叫什么名字','我有一只猫叫合成米粒',True),
    ('我喜欢和朋友一起做什么','我喜欢和朋友一起阅读',True),
    ('你叫什么名字','我叫合成小岚',False),
])
def test_typed_positive_and_negative_evidence(query,fact,expected):
    assert compatible(evidence_need(query),fact) is expected


def test_name_cannot_be_squeezed_out_or_subject_confused():
    now=datetime(2026,11,3);query='我的名字是合成别名，对吗？'
    rows=[SimpleNamespace(id='own',fact='我叫合成阿澄',slot='name',embedding=embed('我叫合成阿澄'),importance=.1,updated_at=now)]
    rows += [SimpleNamespace(id=f'pet{i}',fact=f'我的猫咪叫合成{i}',slot='event',embedding=embed(query),importance=1.,updated_at=now) for i in range(40)]
    policy=RetrievalPolicy(candidate_limit=20,domain_admission=False)
    assert [r.id for r in rank_memories(rows,query,now=now,policy=policy,vector_ids=set())]==['own']
    assert rank_memories(rows[1:],query,now=now,policy=policy)==[]
    assert [r.id for r in rank_memories(rows,'我的名字是什么，不是朋友的名字',now=now,policy=policy)]==['own']


def test_scope_guards_do_not_reject_all_queries_or_reuse_current_for_past():
    report=evaluate_retrieval(REGRESSION_DATASET)
    old=report['variants']['D_rerank']['metrics'];fixed=report['variants']['F_retrieval_fix']['metrics']
    assert report['queries']==21 and fixed['positive_queries']==13 and fixed['negative_queries']==8
    assert old['hits']==13 and old['false_retrieval_count']==7
    assert fixed['hits']==fixed['relevant']==14 and fixed['false_retrieval_count']==0


def test_same_frozen_cases_separate_routing_from_evidence_guard():
    r=evaluate_retrieval();v=r['variants']
    assert v['D_rerank']['metrics']['hits']==36 and v['D_rerank']['metrics']['false_retrieval_count']==2
    assert v['R_identity']['metrics']['hits']==37 and v['R_identity']['metrics']['false_retrieval_count']==2
    assert v['S_evidence']['metrics']['hits']==36 and v['S_evidence']['metrics']['false_retrieval_count']==0
    assert v['F_retrieval_fix']['metrics']['hits']==37 and v['F_retrieval_fix']['metrics']['false_retrieval_count']==0
    fixed={q['id']:q for q in v['F_retrieval_fix']['per_query']}
    assert fixed['name-correction']['ids']==['m01']
    assert fixed['unknown-passport']['ids']==fixed['unknown-childhood']['ids']==[]


def test_fixed_prompt_trials_have_routed_name_and_empty_unknown_context():
    class Provider:
        async def generate(self,history,prompt):return '这只是合成测试。'
    r=asyncio.run(compare_prompts(Provider(),limit=3,repeats=1,max_calls=6,retrieval_variant='F_retrieval_fix'))
    assert r['retrieval_variant']=='F_retrieval_fix' and r['api_calls']==6
    assert all(t['evidence_ids']==['m01'] for t in r['trials'] if t['id']=='name-correction')
    assert all(not t['evidence_ids'] for t in r['trials'] if t['id']=='unknown-passport')
    with pytest.raises(ValueError):asyncio.run(compare_prompts(Provider(),retrieval_variant='unknown'))
