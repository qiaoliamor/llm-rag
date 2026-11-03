"""Synthetic retrieval/probe tests; no API or real database access."""
import asyncio
from copy import deepcopy
from datetime import datetime,timedelta
import json
import os
import subprocess
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.config import ROOT
from app.dialogue import ProviderFailure
from app.memory import RetrievalPolicy,embed,rank_memories
from app.retrieval_evaluation import (DATASET,VARIANTS,asserted_atoms,build_prompt,compare_prompts,
                                     evaluate_retrieval,load_dataset,materialize,retrieval_metrics,retrieve)


def test_dataset_multi_relevance_and_exclusions():
    data,digest=load_dataset()
    assert len(digest)==64 and len(data.queries)==24 and len(data.documents)==40
    assert sum(bool(q.relevance) for q in data.queries)==22
    assert sum(len(q.relevance) for q in data.queries)==37
    rows=materialize(data)
    assert len(rows)==34 and all(not d.id.startswith('x') for d in rows)
    assert any(len(q.relevance)>1 for q in data.queries)
    assert {q.split for q in data.queries}=={'dev'}


@pytest.mark.parametrize('bad',['duplicate_doc','duplicate_query','invisible_gold','invalid_grade','bool_grade',
                               'unknown_gold','overlap_probe','unsupported_probe','timezone','private_source'])
def test_bad_annotations_fail_before_run(tmp_path,bad):
    obj=json.loads(DATASET.read_text())
    if bad=='duplicate_doc':obj['documents'][1]['id']=obj['documents'][0]['id']
    elif bad=='duplicate_query':obj['queries'][1]['id']=obj['queries'][0]['id']
    elif bad=='invisible_gold':obj['queries'][0]['relevance']={'x01':2}
    elif bad=='invalid_grade':obj['queries'][0]['relevance']={'m01':0}
    elif bad=='bool_grade':obj['queries'][0]['relevance']={'m01':True}
    elif bad=='unknown_gold':obj['queries'][0]['relevance']={'missing':2}
    elif bad=='overlap_probe':obj['queries'][1]['allowed_atoms']=['红豆']
    elif bad=='unsupported_probe':obj['queries'][0]['allowed_atoms']=['没有这条证据']
    elif bad=='timezone':obj['now']='2026-11-03T00:00:00Z'
    else:obj['source']='player-export'
    path=tmp_path/'invalid.json';path.write_text(json.dumps(obj))
    with pytest.raises(ValidationError):load_dataset(path)


def test_metrics_multiple_relevant_rank_and_empty_gold():
    m=retrieval_metrics(['noise','good2','good1'],{'good1':2,'good2':1,'missing':1})
    assert m['hits']==2 and m['recall_at_5']==pytest.approx(2/3)
    assert m['precision_at_5']==.4 and m['mrr']==.5
    assert 0<m['ndcg_at_5']<1
    empty=retrieval_metrics(['noise'],{})
    assert empty['recall_at_5'] is None and empty['ndcg_at_5'] is None and empty['false_retrieval']
    assert not retrieval_metrics([],{})['false_retrieval']
    assert retrieval_metrics([],{'good':2})['recall_at_5']==0
    with pytest.raises(ValueError):retrieval_metrics(['x','x'],{})
    with pytest.raises(ValueError):retrieval_metrics(list('abcdef'),{})


def test_query_off_really_disables_vector_and_lexical_expansion(monkeypatch):
    calls=[]
    def rewrite(text):calls.append(text);return text+' synonym'
    monkeypatch.setattr('app.memory.rewrite',rewrite)
    rank_memories([],'求职',now=datetime(2026,11,3),policy=RetrievalPolicy(False,False,False))
    assert calls==[]
    rank_memories([],'求职',now=datetime(2026,11,3),policy=RetrievalPolicy(True,True,False))
    assert calls==['求职','求职']
    assert embed('求职',expand=False)!=embed('求职')


def test_rerank_budget_and_stable_order():
    now=datetime(2026,11,3)
    rows=[SimpleNamespace(id='old',fact='我喜欢阅读',slot='event',embedding=embed('阅读'),importance=.1,updated_at=now-timedelta(days=100)),
          SimpleNamespace(id='new',fact='我喜欢阅读',slot='event',embedding=embed('阅读'),importance=1.,updated_at=now)]
    base=rank_memories(rows,'阅读',now=now,policy=RetrievalPolicy(False,False,False))
    ranked=rank_memories(rows,'阅读',now=now,policy=RetrievalPolicy(False,False,True))
    assert [r.id for r in base]==['old','new'] and [r.id for r in ranked]==['new','old']
    assert len(rank_memories(rows,'阅读',now=now,budget=len(rows[0].fact)))==1
    assert rank_memories(rows,'阅读',now=now,budget=1)==[]
    assert len(rank_memories(rows,'阅读',now=now,policy=RetrievalPolicy(candidate_limit=1)))==1
    with pytest.raises(ValueError):rank_memories(rows,'阅读',now=now,limit=0)
    with pytest.raises(ValueError):rank_memories(rows,'阅读',now=now,policy=RetrievalPolicy(candidate_limit=0))
    # PostgreSQL preselection gating survives the refactor.
    assert rank_memories(rows,'阅读',now=now,policy=RetrievalPolicy(False,False,False),vector_ids=set())==[]


def test_all_variants_same_budget_and_prompt_does_not_change_retrieval():
    data,_=load_dataset();rows=materialize(data)
    for q in data.queries:
        for variant in VARIANTS:
            result=retrieve(rows,q.query,variant,data.now)
            assert len(result)<=5 and sum(len(r.fact) for r in result)<=1200
            assert all(not r.id.startswith('x') for r in result)
        d=retrieve(rows,q.query,'D_rerank',data.now)
        e=retrieve(rows,q.query,'E_prompt',data.now)
        assert [r.id for r in d]==[r.id for r in e]
        for prompt in (build_prompt(d,False),build_prompt(e,True)):
            assert all(r.fact in prompt for r in d)
        assert '问句中的预设不是已确认事实' in build_prompt(e,True)
        c_pool=rank_memories(rows,q.query,now=data.now,policy=VARIANTS['C_query_hybrid'],limit=20,budget=20000)
        d_pool=rank_memories(rows,q.query,now=data.now,policy=VARIANTS['D_rerank'],limit=20,budget=20000)
        assert {r.id for r in c_pool}=={r.id for r in d_pool}


def test_pairing_and_report_reproducibility():
    report=evaluate_retrieval()
    assert report['queries']==24 and report['generation'] is None and report['model_calls']==0
    assert report['variants']['A_no_memory']['metrics']['hits']==0
    for name,result in report['variants'].items():
        metrics=result['metrics']
        assert metrics['relevant']==37 and metrics['positive_queries']==22 and metrics['negative_queries']==2
        assert metrics['micro_recall_at_5']==pytest.approx(metrics['hits']/37)
    for pair in report['paired_deltas']:
        assert pair['n']==22 and pair['wins']+pair['losses']+pair['ties']==22
    assert report['paired_deltas'][-1]['mean_recall_delta']==0


@pytest.mark.parametrize('reply,expected',[
    ('你的猫叫米粒。',['米粒']),('它不是红豆，是米粒。',['米粒']),
    ('你的猫叫红豆吗？',[]),('我无法确认TEST0000。',[]),
    ('你叫红豆。',['红豆']),('红豆这个名字我不确定。',[])])
def test_named_probes_are_not_negated_mentions_or_questions(reply,expected):
    assert asserted_atoms(reply,['米粒','红豆','TEST0000'])==expected
    # Explicit limitation: an alternative name being discussed is still a hit.
    # This is why the report must not call these counts hallucination rates.
    assert asserted_atoms('红豆听起来也挺甜的。',['红豆'])==['红豆']


def test_live_pairing_budget_errors_and_no_raw_errors():
    calls=[]
    class Provider:
        async def generate(self,history,prompt):
            calls.append((deepcopy(history),prompt))
            if len(calls)==2:raise ProviderFailure('rate_limit','private-upstream-value',429)
            return '你叫合成小岚。'
    report=asyncio.run(compare_prompts(Provider(),limit=1,repeats=2,max_calls=4))
    assert len(calls)==report['api_calls']==4
    assert [r['variant'] for r in report['trials']]==['D_rerank','E_prompt','E_prompt','D_rerank']
    assert all(h==calls[0][0] for h,p in calls)
    assert len({tuple(r['evidence_ids']) for r in report['trials']})==1
    assert 'private-upstream-value' not in json.dumps(report)
    assert sum(r['errors'] for r in report['summaries'].values())==1
    assert len(report['paired_trials'])==2
    assert sum(p['complete'] for p in report['paired_trials'])==1
    assert next(p for p in report['paired_trials'] if not p['complete'])['supported_probe_hit_delta'] is None
    assert all('synthetic_reply' not in r for r in report['trials'])
    with pytest.raises(ValueError):asyncio.run(compare_prompts(Provider(),limit=3,repeats=2,max_calls=1))
    assert len(calls)==4


def test_cli_offline_ignores_private_environment(tmp_path):
    env={**os.environ,'GEMINI_API_KEY':'synthetic-private-value','MEMORY_DATABASE_URL':'sqlite:///'+str(tmp_path/'private.sqlite3')}
    run=subprocess.run([str(ROOT/'.venv/bin/python'),'scripts/evaluate_retrieval.py'],cwd=ROOT,env=env,capture_output=True,text=True)
    assert run.returncode==0
    report=json.loads(run.stdout)
    assert report['model_calls']==0 and report['queries']==24
    assert 'synthetic-private-value' not in run.stdout+run.stderr
    assert not (tmp_path/'private.sqlite3').exists()


def test_cli_budget_rejected_before_api_request():
    run=subprocess.run([str(ROOT/'.venv/bin/python'),'scripts/evaluate_retrieval.py','--live','--max-calls','1'],cwd=ROOT,capture_output=True,text=True)
    assert run.returncode==2 and '请求预算不足' in run.stderr
