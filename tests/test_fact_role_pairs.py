"""Synthetic bookkeeping checks, deliberately not a semantic oracle."""
import json
import subprocess
import sys

import pytest
from pydantic import ValidationError
from app.narrative_calibration import load_dataset, score, summarize
from app.semantic_review import Review, ReviewOutcome
from scripts.check_fact_role_pairs import DATASET, Dataset, validate


def load():
    return load_dataset(DATASET, model=Dataset)[0]


@pytest.mark.parametrize('pair', load().pairs, ids=lambda p: p.family)
def test_pair_context_and_reference_are_not_injected(pair):
    for case in (pair.allowed, pair.violating):
        history, evidence = case.context()
        assert history[-1]['role'] == 'user'
        assert {e['id'] for e in evidence} >= {'role_profile', 'scene_profile'}
        serialized = json.dumps(evidence, ensure_ascii=False)
        assert case.rationale not in serialized
        assert 'fact_issue' not in serialized and 'role_issue' not in serialized
        assert not case.prior_failure
    assert pair.allowed.context() == pair.violating.context()


@pytest.mark.parametrize('pair', load().pairs, ids=lambda p: p.family)
def test_always_accept_mock_exposes_wrong_axis_not_quality(pair):
    # A deliberately wrong mock must not earn credit on the violating reply.
    outcome = ReviewOutcome('accept', Review(decision='accept', confidence=.9,
        role_issues=[], segments=[dict(text=pair.violating.reply,
        kind='assertion', verdict='supported', evidence_ids=['scene_profile'],
        reason='evidence_supports')]))
    rows = [score(c, outcome) for c in (pair.allowed, pair.violating)]
    report = summarize(rows)
    assert report['both_axes_matches'] == 1
    assert report[pair.axis + '_issue']['fn'] == 1


@pytest.mark.parametrize('status,failure', [
    ('unavailable', 'timeout'), ('unavailable', 'http_503'),
    ('unavailable', 'invalid_output'), ('uncertain', 'low_confidence')])
def test_all_failures_stay_failures(status, failure):
    cases = [c for p in load().pairs for c in (p.allowed, p.violating)]
    report = summarize([score(c, ReviewOutcome(status, None, failure)) for c in cases])
    assert report['attempts'] == 16 and report['usable'] == 0
    assert report['both_axes_matches'] == 0
    assert report['failures'] == {failure: 16}


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(source='real'),
    lambda d: d.update(annotation_method='independent'),
    lambda d: d['pairs'].pop(),
    lambda d: d['pairs'].append(d['pairs'][0]),
    lambda d: d['pairs'][0]['allowed'].update(fact_issue=True),
    lambda d: d['pairs'][0]['violating'].update(role_issue=True),
    lambda d: d['pairs'][0]['violating'].update(history=[{'role':'user','content':'other'}]),
    lambda d: d['pairs'][0]['violating'].update(reply=d['pairs'][0]['allowed']['reply']),
    lambda d: d['pairs'][1]['allowed'].update(id=d['pairs'][0]['allowed']['id']),
    lambda d: d['pairs'][0]['allowed'].update(prior_failure='invented provenance'),
])
def test_invalid_preparation_is_rejected(mutation):
    raw = json.loads(DATASET.read_text())
    mutation(raw)
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw)


@pytest.mark.parametrize('field', ['scene_sha256', 'character_sha256'])
def test_policy_drift_rejected(tmp_path, field):
    raw = json.loads(DATASET.read_text())
    raw[field] = '0' * 64
    path = tmp_path / 'synthetic.json'
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match='policy drift'):
        load_dataset(path, model=Dataset)


def test_cli_has_no_live_mode_or_quality_claim():
    result = subprocess.run([sys.executable, 'scripts/check_fact_role_pairs.py'],
                            capture_output=True, text=True, check=True)
    report = json.loads(result.stdout)
    assert report == validate()
    assert report['max_calls'] == 0 and report['cases'] == 16
    assert report['acceptance'] == 'not_assessed'
    result = subprocess.run([sys.executable, 'scripts/check_fact_role_pairs.py', '--live'],
                            capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
