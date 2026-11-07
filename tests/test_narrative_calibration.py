import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.narrative_calibration import DATASET, Dataset, LIVE_IDS, load_dataset, score, summarize
from app.semantic_review import Review, ReviewOutcome, review_reply
from scripts.evaluate_narrative_calibration import evaluate


def reference_outcome(case):
    # Synthetic reference-shaped responses test bookkeeping, NEVER model accuracy.
    bad = case.fact_issue
    return ReviewOutcome(case.expected, Review(decision=case.expected, confidence=0.9,
        role_issues=[0] if case.role_issue else [], segments=[dict(text=case.reply,
        kind='assertion', verdict='unsupported' if bad else 'supported',
        evidence_ids=[] if bad else ['scene_profile'],
        reason='missing_evidence' if bad else 'evidence_supports')]))


@pytest.mark.parametrize('case', load_dataset()[0].cases, ids=lambda c:c.id)
def test_each_reference_axis_scoring(case):
    row = score(case, reference_outcome(case))
    assert row['axes_match'] and row['decision_match']
    history, evidence = case.context()
    assert history[-1]['role'] == 'user'
    assert all('fact_issue' not in e and 'rationale' not in e for e in evidence)
    assert {e['id'] for e in evidence} >= {'scene_profile', 'role_profile'}


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(source='real'),
    lambda d: d['cases'].append(d['cases'][0]),
    lambda d: d['cases'][0].update(fact_issue='true'),
    lambda d: d['cases'][0].update(prior_failure=None),
    lambda d: d['cases'][2].update(prior_failure='arbitrary failure'),
    lambda d: d['cases'][0].update(history=[{'role':'assistant','content':'hello'}]),
    lambda d: d['cases'][0].update(unexpected='secret'),
    lambda d: d['cases'][0].update(memories=[{'id':'m','fact':'test','event_date':'bad'}]),
])
def test_reject_invalid_manifest(mutation):
    data = json.loads(DATASET.read_text())
    mutation(data)
    with pytest.raises(ValidationError):
        Dataset.model_validate(data)


@pytest.mark.parametrize('key', ['scene_sha256','character_sha256'])
def test_policy_drift_fails(tmp_path,key):
    data = json.loads(DATASET.read_text())
    data[key] = '0'*64
    path = tmp_path/'synthetic.json'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='policy drift'):
        load_dataset(path)


def test_legacy_is_frozen_and_live_context_unchanged():
    legacy = Path('evaluations/fact_support_dev.json').read_bytes()
    assert hashlib.sha256(legacy).hexdigest() == 'f3a2f1d8c4a7559598464479147e007df02031d23074bb952a6bb8134bf4ad19'
    from scripts.compare_semantic_review import cases
    old,_ = cases()
    for case in load_dataset()[0].cases:
        if case.id in LIVE_IDS:
            prior = next(c for c in old if c['id']==case.id)
            assert case.reply == prior['candidate']
            assert case.history[0].content == prior['query']
            assert [m.model_dump() for m in case.memories] == prior['memories']


def test_axes_not_hidden_by_correct_final_revise():
    case = next(c for c in load_dataset()[0].cases if c.id=='role-and-fact')
    result = reference_outcome(case)
    result.result.role_issues.clear()
    row = score(case,result)
    assert row['decision_match'] and not row['axes_match']
    summary = summarize([row])
    assert summary['role_issue']['fn']==1 and summary['fact_issue']['tp']==1


@pytest.mark.parametrize('status,failure', [('unavailable','timeout'),('unavailable','invalid_output'),('uncertain','low_confidence')])
def test_failure_not_success_or_false_accept(status,failure):
    case = load_dataset()[0].cases[0]
    row = score(case,ReviewOutcome(status,None,failure))
    summary = summarize([row])
    assert summary['attempts']==1 and summary['usable']==0
    assert not row['axes_match'] and not row['decision_match']
    assert all(v==0 for v in summary['fact_issue'].values())
    assert summary['failures']=={failure:1}


def test_live_cap_and_no_reference_leakage():
    class Fake:
        calls=0
        async def review(self,reply,history,evidence):
            self.calls+=1
            assert all('expected' not in item and 'rationale' not in item for item in evidence)
            case=next(c for c in load_dataset()[0].cases if c.reply==reply)
            return reference_outcome(case).result
    provider=Fake()
    rows=asyncio.run(evaluate(provider,load_dataset()[0]))
    assert provider.calls==2 and {r['id'] for r in rows}==set(LIVE_IDS)
    assert summarize(rows)['both_axes_matches']==2


def test_service_failure_stops_without_retry():
    class Fake:
        calls=0
        async def review(self,*args):
            self.calls+=1
            raise TimeoutError()
    provider=Fake()
    rows=asyncio.run(evaluate(provider,load_dataset()[0]))
    assert provider.calls==1 and rows[0]['failure']=='timeout'


def test_unknown_evidence_not_counted_as_correct():
    case=load_dataset()[0].cases[1]
    class Fake:
        async def review(self,*args):
            review=reference_outcome(case).result
            review.segments[0].evidence_ids=['other_players_memory']
            return review
    history,evidence=case.context()
    result=asyncio.run(review_reply(Fake(),case.reply,history,evidence))
    assert result.failure=='unknown_evidence'
    assert not score(case,result)['decision_match']


def test_offline_cli_never_loads_config_or_calls_api():
    result=subprocess.run([sys.executable,'scripts/evaluate_narrative_calibration.py'],capture_output=True,text=True,check=True)
    report=json.loads(result.stdout)
    assert report['mode']=='manifest_validation_only' and report['max_calls']==0
    assert 'results' not in report and report['case_count']==23
