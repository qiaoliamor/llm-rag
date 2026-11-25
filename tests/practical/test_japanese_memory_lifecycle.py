import pytest

from app.config import Settings
from scripts import retest_japanese_memory_lifecycle as lifecycle


class Understanding:
    async def analyze(self, data):
        assert data['recent_dialogue'] == [{'role': 'user', 'content': lifecycle.QUESTION}]
        return lifecycle.plan('住んでいる市', ['residence'])

    async def select(self, data):
        assert len(data['candidates']) == 1
        return {'ids': [data['candidates'][0]['id']], 'confidence': 1.0}


class Generator:
    async def generate(self, history, prompt):
        assert history == [{'role': 'user', 'content': lifecycle.QUESTION}]
        for fact in (lifecycle.OLD, lifecycle.NEW):
            if fact in prompt:
                return fact
        return '今は思い出せないな。よかったら教えて。'


class Judge:
    def __init__(self, timeout=False):
        self.timeout = timeout

    async def review(self, reply, history, evidence):
        if self.timeout:
            raise TimeoutError()
        ids = [e['id'] for e in evidence if e['kind'] == 'memory']
        return {'decision': 'accept', 'confidence': 1.0, 'role_issues': [],
                'segments': [{'text': reply, 'kind': 'assertion' if ids else 'nonfactual',
                              'verdict': 'supported' if ids else 'not_applicable',
                              'reason': 'evidence_supports' if ids else 'nonfactual',
                              'evidence_ids': ids}]}


@pytest.mark.parametrize('failure', [False, True])
def test_japanese_memory_lifecycle(failure):
    settings = Settings(_env_file=None, chat_provider='mock', weather_provider='mock',
                        growth_enabled=True, dialogue_mode='companion', reply_review_policy='contextual',
                        memory_understanding_mode='semantic', reply_understanding_mode='semantic',
                        weather_understanding_mode='semantic', emotion_understanding_mode='semantic')
    report = lifecycle.run(settings, Understanding(), Generator(), Judge(timeout=failure))
    if failure:
        assert report['unexecuted'] == ('corrected', 'deleted')
        assert report['rows'][0]['failure'] == 'review_busy'
        assert report['rows'][0]['saved'] == 0
        assert len(report['calls']) == 4
    else:
        assert not report['unexecuted']
        assert not report['blocked']
        assert len(report['calls']) == 10
        assert [row['projected'] for row in report['rows']] == [[lifecycle.OLD], [lifecycle.NEW], []]
        assert all(row['complete'] and row['saved'] == 2 for row in report['rows'])
        assert report['rows'][-1]['review'] == {'status': 'prompt_only', 'calls': 0}
        assert report['rows'][-1]['reply'] == '今は思い出せないな。よかったら教えて。'


def test_full_policy_keeps_review_after_deletion():
    settings = Settings(_env_file=None, chat_provider='mock', weather_provider='mock',
                        growth_enabled=True, dialogue_mode='companion', reply_review_policy='full',
                        memory_understanding_mode='semantic', reply_understanding_mode='semantic',
                        weather_understanding_mode='semantic', emotion_understanding_mode='semantic')
    report = lifecycle.run(settings, Understanding(), Generator(), Judge())
    assert len(report['calls']) == 11
    assert report['calls'][-1]['state'] == 'deleted'
    assert report['calls'][-1]['kind'] == 'review'
    assert report['rows'][-1]['review']['status'] == 'accepted'


def test_selection_uncertain_still_reviews_memory_request():
    class UncertainSelection(Understanding):
        async def select(self, data):
            return {'ids': [], 'confidence': 0.5}

    settings = Settings(_env_file=None, chat_provider='mock', weather_provider='mock',
                        growth_enabled=True, dialogue_mode='companion', reply_review_policy='contextual',
                        memory_understanding_mode='semantic', reply_understanding_mode='semantic',
                        weather_understanding_mode='semantic', emotion_understanding_mode='semantic')
    report = lifecycle.run(settings, UncertainSelection(), Generator(), Judge())
    assert report['rows'][0]['memory']['selection'] == 'uncertain'
    assert report['rows'][0]['review']['status'] == 'accepted'
    assert not report['rows'][0]['complete']
    assert report['unexecuted'] == ('corrected', 'deleted')
