"""Subject-specific memory selection using mock SDK verdicts and real storage/API paths."""
import pytest
from test_budget import context
from test_understanding import plan
from app.memory_understanding import MemoryMetadata


@pytest.mark.parametrize('who,query,relevant',[
    ('妹の面接先、覚えてる？','妹 面接','sister'),
    ('私の面接先、覚えてる？','私 面接','own'),
])
def test_subject_specific_selection_not_first_candidate_and_actual_prompt_projection(context,monkeypatch,who,query,relevant):
    x=context;uid=next(iter(x.c.app.state.sessions.values())).user_id
    records={}
    for label,text in [('own','私は合成葵社の面接を受けました。'),('sister','妹は合成桔梗社の面接を受けました。')]:
        m=x.store.candidate(uid,text,'synthetic',x.store.settings(uid)['epoch'],manual=True,metadata=MemoryMetadata('event','event'))
        records[label]=x.store.mutate(uid,m['id'],m['version'],confirm=True)
    x.analyst.analyze.side_effect=None
    x.analyst.analyze.return_value=plan(need=True,query=query,target_slots=['history'])
    x.analyst.select.return_value={'ids':[records[relevant]['id']],'confidence':.95}
    # Deliberately reverse candidates; the reference is semantic, not rank zero.
    original=x.store.semantic_candidates
    def reversed_candidates(*args,**kwargs):return list(reversed(original(*args,**kwargs)))
    monkeypatch.setattr(x.store,'semantic_candidates',reversed_candidates)
    r=x.c.post('/v1/chat',headers=x.h,json={'message':who,'locale':'ja-JP'})
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[records[relevant]['id']]
    shown=x.analyst.select.call_args.args[0]['candidates']
    assert {records['own']['id'],records['sister']['id']} <= {m['id'] for m in shown}
    prompt=x.provider.generate.call_args.args[1]
    assert records[relevant]['fact'] in prompt
    other='own' if relevant=='sister' else 'sister'
    assert records[other]['fact'] not in prompt
    # This plan/selection is authored, not a measured model prediction.


def test_no_answer_for_other_relative_does_not_borrow_sister_record(context):
    x=context;uid=next(iter(x.c.app.state.sessions.values())).user_id
    text='妹は合成桔梗社の面接を受けました。'
    m=x.store.candidate(uid,text,'synthetic',x.store.settings(uid)['epoch'],manual=True,metadata=MemoryMetadata('event','event'))
    x.store.mutate(uid,m['id'],m['version'],confirm=True)
    x.analyst.analyze.side_effect=None
    x.analyst.analyze.return_value=plan(need=True,query='姉 面接',target_slots=['history'])
    x.analyst.select.return_value={'ids':[],'confidence':.95}
    r=x.c.post('/v1/chat',headers=x.h,json={'message':'姉の面接先は？','locale':'ja-JP'})
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[]
    assert text not in x.provider.generate.call_args.args[1]
