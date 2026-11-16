"""Same-language references are authored scripts, never Gemini predictions."""
import os
import pytest
from app import japanese_memory_layers as e


@pytest.fixture(scope='module')
def same_report():return e.evaluate(e.SAME_LANGUAGE_DATASET)


def test_separate_same_language_denominator_preserves_wrong_accepts(same_report):
    p=same_report
    assert p['scope']=='same_language' and p['cases']==10 and p['attempted']==26
    assert p['model_calls']==0 and p['assessment']=='not_assessed'
    assert p['reference_probes']=={'attempted':10,'reference_answer_complete':10,'candidate_misses':0}
    assert p['published_with_unsupported_claims']==8 and p['projection_mismatches']==0
    for prefix in ('zh-','ja-'):
        rows=[r for r in p['per_probe'] if r['case'].startswith(prefix) and r['probe']=='reference']
        assert len(rows)==5 and all(r['reply']['reference_answer_complete'] for r in rows)
        no_answer=next(r for r in rows if r['case'].endswith('no-answer'))
        assert no_answer['selection']['ids']==[] and no_answer['context']['ids']==[]
        correction=next(r for r in rows if r['case'].endswith('current-correction'))
        assert correction['candidate']['ids'] is None and correction['selection']['status']=='not_requested'
        assert correction['context']['ids']==[]
        name=next(r for r in rows if r['case'].endswith('name'))
        assert name['candidate']['ids']==name['context']['ids']==['own']


@pytest.mark.parametrize('case',e.load(e.SAME_LANGUAGE_DATASET).cases,ids=lambda c:c.id)
@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_same_language_reference_through_default_api_and_storage(case,backend,tmp_path):
    url=os.environ.get('TEST_POSTGRES_URL') if backend=='postgres' else 'sqlite:///'+str(tmp_path/'same-language.sqlite3')
    if not url:pytest.skip('requires script-created temporary PostgreSQL')
    row=e._run_probe(case,e.Probe(id='reference'),url)
    assert row['http_status']==200 and row['reply']['reference_answer_complete']
    assert row['reply']['unsupported_claims']==0 and row['context']['projection_match']
    assert row['state']['saved_messages']==2
