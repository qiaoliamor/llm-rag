"""Synthetic M5 runner contracts and fixes; never run the held-out scenarios here."""
import json
import os
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import ROOT, Settings
from app.dialogue import FALLBACK, conflicts
from app.evaluation import DATASET, evaluate, load_cases, percentile
from app.main import create_app


def test_dataset_counts_and_group_split():
    data, digest = load_cases()
    cases = data['cases']
    assert len(digest) == 64
    assert {k: sum(c['category'] == k for c in cases) for k in
            ('memory','canon','weather','emotion','security')} == {
                'memory':25,'canon':25,'weather':20,'emotion':20,'security':10}
    assert sum(c['split'] == 'dev' for c in cases) == 68
    assert sum(c['split'] == 'holdout' for c in cases) == 32


@pytest.mark.parametrize('mutation', ['duplicate','leak','label','missing','category','operation','source','empty'])
def test_invalid_dataset_fails_before_execution(tmp_path, mutation):
    data = json.loads(DATASET.read_text())
    cases = data['cases']
    if mutation == 'duplicate': cases[1]['id'] = cases[0]['id']
    elif mutation == 'leak': cases[1]['split'] = 'holdout'
    elif mutation == 'label': next(c for c in cases if c['category'] == 'emotion')['expected'] = ['invented']
    elif mutation == 'missing': del cases[0]['fact']
    elif mutation == 'category': cases[0]['category'] = 'invented'
    elif mutation == 'operation': cases[-1]['operation'] = 'invented'
    elif mutation == 'source': data['source'] = 'player-export'
    else: data['cases'] = []
    path = tmp_path / 'invalid.json'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError): load_cases(path)


def test_dev_baseline_uses_only_temporary_storage(monkeypatch, tmp_path):
    private = tmp_path / 'do-not-touch.sqlite3'
    monkeypatch.setenv('MEMORY_DATABASE_URL', 'sqlite:///' + str(private))
    report = evaluate()
    assert report['passed'] == report['total'] == 68
    assert all(r['split'] == 'dev' for r in report['results'])
    assert report['categories']['memory']['recall_at_5'] == {'hits':15,'relevant':15,'value':1.0}
    assert report['categories']['weather']['tp'] == 8
    assert report['model_calls'] == report['weather_api_calls'] == 0
    assert not private.exists()
    assert report['component_latency_ms']['p95'] >= report['component_latency_ms']['p50'] >= 0


def test_metrics_include_false_positives_and_failures(monkeypatch, tmp_path):
    data = {'source':'synthetic','version':'test','cases':[
        {'id':'w1','group':'a','category':'weather','split':'dev','message':'合成1','expected':True},
        {'id':'w2','group':'b','category':'weather','split':'dev','message':'合成2','expected':False},
        {'id':'w3','group':'c','category':'weather','split':'dev','message':'合成3','expected':True}]}
    path = tmp_path / 'cases.json'; path.write_text(json.dumps(data))
    monkeypatch.setattr('app.evaluation.run_case', lambda c: {
        'prediction': c['id'] != 'w3', 'expected': c['expected'],
        'passed': (c['id'] != 'w3') == c['expected']})
    report = evaluate(path=path)
    weather = report['categories']['weather']
    assert report['passed'] == 1 and report['total'] == 3
    assert weather['tp'] == weather['fp'] == weather['fn'] == 1
    assert weather['precision'] == weather['recall'] == .5
    monkeypatch.setattr('app.evaluation.run_case', lambda c: {'prediction':False,'expected':False,'passed':True})
    assert evaluate(path=path)['categories']['weather']['precision'] is None


def test_unexpected_runner_errors_are_not_swallowed(monkeypatch):
    def fail(case): raise RuntimeError('synthetic-runner-failure')
    monkeypatch.setattr('app.evaluation.run_case', fail)
    with pytest.raises(RuntimeError): evaluate()
    with pytest.raises(ValueError): evaluate(split='invented')


def test_percentiles_use_nearest_rank():
    assert percentile([], .95) is None
    assert percentile([30, 10, 20], .5) == 20
    assert percentile([30, 10, 20], .95) == 30


def test_cli_is_offline_and_never_prints_environment(tmp_path):
    env = {**os.environ,'GEMINI_API_KEY':'synthetic-never-print','OPENAI_API_KEY':'synthetic-never-print',
           'MEMORY_DATABASE_URL':'sqlite:///' + str(tmp_path / 'private.sqlite3')}
    run = subprocess.run([str(ROOT/'.venv/bin/python'),'scripts/evaluate_m5.py'], cwd=ROOT,
                         env=env, capture_output=True, text=True)
    assert run.returncode == 0
    report = json.loads(run.stdout)
    assert report['total'] == 68 and report['provider'] == 'none'
    assert 'synthetic-never-print' not in run.stdout + run.stderr
    assert not (tmp_path/'private.sqlite3').exists()


def test_cli_returns_nonzero_for_failed_assertions(monkeypatch, capsys):
    from scripts import evaluate_m5
    monkeypatch.setattr('sys.argv', ['evaluate_m5.py'])
    monkeypatch.setattr(evaluate_m5, 'evaluate', lambda split: {'passed':0, 'total':1})
    assert evaluate_m5.main() == 1
    assert json.loads(capsys.readouterr().out)['passed'] == 0


@pytest.mark.parametrize('reply,query,expected', [
    ('我今年二十九岁。','年龄',True),
    ('我今年二十八岁。','年龄',False),
    ('我今年028岁。','年龄',False),
    ('她今年19岁。','年龄',False),
    ('你说“我今年19岁”。','年龄',False),
    ('“我今年19岁”。','年龄',True),
    ('"我今年二十九岁"','年龄',True),
    ('「我是医生」。','职业',True),
    ('“我今年28岁”，但我今年19岁。','年龄',True),
    ('旧书店并非继承而来。','书店',False),
    ('朋友的书店是继承的。','书店',False),
    ('我没有继承书店，但是这家店是亲人传给我的。','书店',True),
    ('我不是演员，但我是医生。','职业',True),
    ('我不太记得小时候住在哪里。','你小时候住在哪里',True),
    ('那段记忆已经记不清了。','你的童年',True),
    ('你说“我不太记得小时候住在哪里”。','你的童年',False),
    ('这件事我还不能确定，不想随口编一个答案。','你的童年',False),
    ('我不太记得这本书放哪了。','书放哪了',False),
])
def test_targeted_canon_guard_regressions(reply, query, expected):
    assert conflicts(reply, query) is expected


@pytest.mark.parametrize('second,expected', [('我不知道，不能随口补写。','我不知道，不能随口补写。'),
                                          ('我不太记得小时候住哪。',FALLBACK)])
def test_unknown_background_rewrite_and_fallback(second, expected):
    provider = SimpleNamespace(generate=AsyncMock(side_effect=['我不太记得小时候住哪。',second]))
    client = TestClient(create_app(Settings(_env_file=None, chat_provider='mock'), provider))
    session = client.get('/v1/session').json()
    result = client.post('/v1/chat', headers={'x-csrf-token':session['csrf_token']},
                         json={'message':'你小时候和父母住在哪里？'})
    assert result.status_code == 200 and result.json()['guarded']
    assert result.json()['reply'] == expected
    assert provider.generate.await_count == 2
    assert client.get('/v1/session').json()['messages'][-1]['content'] == expected
