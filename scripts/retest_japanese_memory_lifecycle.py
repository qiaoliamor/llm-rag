"""Three fixed synthetic memory turns through FastAPI. Live Gemini requires --live."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from time import monotonic
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.config import ROOT, Settings
from app.dialogue import ProviderFailure, build_provider
from app.fact_presentation import FactAnalysisProvider
from app.memory_understanding import ModelMemoryUnderstanding

OLD = '私は合成青梧市に住んでいます。'
NEW = '私は合成桔梗市に住んでいます。'
QUESTION = '私が今住んでいる市を覚えてる？'
STATES = ('confirmed', 'corrected', 'deleted')


def plan(query='', slots=(), candidates=()):
    return {'memory_use': 'allow', 'need_memory': bool(query), 'query': query,
            'target_slots': list(slots), 'confidence': 1.0, 'candidates': list(candidates),
            'reason': 'personal_history_needed' if query else 'current_context_sufficient'}


class BoundedProviders:
    def __init__(self, understanding, generator, judge):
        self.understanding = understanding
        self.generator = generator
        self.judge = judge
        self.calls = []
        self.failed = False
        self.blocked = []
        self.stage = None
        self.draft = None
        self.projected = None

    async def call(self, kind, operation, *args):
        if (self.failed or len(self.calls) >= 12
                or any(c['state'] == self.stage and c['kind'] == kind for c in self.calls)):
            self.blocked.append(kind)
            raise ProviderFailure('test_call_budget', 'Extra test call blocked.', 503)
        row = {'state': self.stage, 'kind': kind}
        self.calls.append(row)
        start = monotonic()
        try:
            result = await operation(*args)
            row['status'] = 'returned'
            return result
        except BaseException as error:
            self.failed = True
            row['status'] = 'failed'
            row['error_type'] = type(error).__name__
            raise
        finally:
            row['seconds'] = round(monotonic() - start, 3)

    async def analyze(self, data):
        if data['operation'] == 'manual_metadata':
            return plan(candidates=[{
                'source_text': data['current_message'], 'subject': 'user', 'actuality': 'asserted',
                'slot': 'residence', 'category': 'profile', 'confidence': 1.0,
                'date': dict(kind='unknown', expression='', absolute=None, days=None,
                             week_offset=None, weekday=None),
            }])
        return await self.call('query', self.understanding.analyze, data)

    async def select(self, data):
        return await self.call('selection', self.understanding.select, data)

    async def generate(self, history, prompt):
        self.projected = [fact for fact in (OLD, NEW) if fact in prompt]
        self.draft = await self.call('generation', self.generator.generate, history, prompt)
        return self.draft

    async def review(self, *args):
        return await self.call('review', self.judge.review, *args)


def run(settings, understanding, generator, judge):
    providers = BoundedProviders(understanding, generator, judge)
    rows = []
    with tempfile.TemporaryDirectory(prefix='ja-memory-lifecycle-') as tmp:
        url = 'sqlite:///' + str(Path(tmp) / 'synthetic.sqlite3')
        # app.main also constructs a module-level app. Isolate that import.
        with patch.dict(Settings.model_config, env_file=None), patch.dict(
                os.environ, CHAT_PROVIDER='mock', WEATHER_PROVIDER='mock',
                MEMORY_DATABASE_URL=url, GEMINI_API_KEY='', OPENAI_API_KEY=''):
            from app.main import create_app
        from app.progression import Bond
        from pydantic import SecretStr

        app = create_app(settings.model_copy(update={'memory_database_url': SecretStr(url)}),
                         provider=providers, memory_understander=providers, semantic_judge=providers)
        store = app.state.memory_store
        try:
            def boot(player=None):
                client = TestClient(app, cookies={'persona_player': player} if player else {})
                response = client.get('/v1/session')
                response.raise_for_status()
                session = response.json()
                assert session['messages'] == []
                return client, {'x-csrf-token': session['csrf_token']}

            owner, headers = boot()
            player = owner.cookies['persona_player']
            uid = next(iter(app.state.sessions.values())).user_id
            with store.db.begin() as db:
                db.get(Bond, (uid, 'shen_yan')).score = 30

            def write(method, path, **kwargs):
                response = owner.request(method, path, headers=headers, **kwargs)
                if response.status_code != 200:
                    raise RuntimeError(f'fixture lifecycle HTTP {response.status_code}')
                return response.json()

            write('PATCH', '/v1/settings', json={'memory_enabled': True, 'timezone': 'Asia/Tokyo'})
            item = write('POST', '/v1/memories', json={'fact': OLD})['item']
            assert item['status'] == 'candidate'
            assert store.semantic_candidates(uid, '住んでいる市', target_slots=['residence']) == []
            path = '/v1/memories/' + item['id']
            item = write('PATCH', path, json={'version': item['version'], 'confirm': True})['item']
            outsider, outside_headers = boot()
            assert outsider.get('/v1/memories').json()['items'] == []
            assert outsider.delete(path, headers=outside_headers, params={'version': item['version']}).status_code == 404
            outsider.close()

            seen_sessions = {owner.cookies['persona_session']}
            for state in STATES:
                if state == 'corrected':
                    stale = owner.patch(path, headers=headers, json={'version': item['version'] - 1, 'fact': NEW})
                    assert stale.status_code == 409
                    item = write('PATCH', path, json={'version': item['version'], 'fact': NEW})['item']
                    assert item['status'] == 'confirmed'
                if state == 'deleted':
                    write('DELETE', path, params={'version': item['version']})
                expected = [] if state == 'deleted' else [OLD if state == 'confirmed' else NEW]
                assert [m['fact'] for m in owner.get('/v1/memories').json()['items']] == expected

                client, chat_headers = boot(player)
                with client:
                    session_id = client.cookies['persona_session']
                    assert session_id not in seen_sessions and app.state.sessions[session_id].user_id == uid
                    seen_sessions.add(session_id)
                    providers.stage = state
                    providers.draft = providers.projected = None
                    start = monotonic()
                    response = client.post('/v1/chat', headers=chat_headers,
                                           json={'message': QUESTION, 'locale': 'ja-JP'})
                    seconds = round(monotonic() - start, 3)
                    body = response.json()
                    expected_ids = [item['id']] if expected else []
                    review = body.get('semantic_review') or {}
                    understanding_result = body.get('memory_understanding') or {}
                    reply = body.get('reply')
                    complete = (response.status_code == 200 and bool(reply)
                                and body.get('retrieved_memory_ids') == expected_ids
                                and providers.projected == expected
                                and understanding_result.get('status') == 'ready'
                                and body['memory_route']['need_memory']
                                and review.get('status') in ('accepted', 'prompt_only'))
                    rows.append({
                        'state': state, 'http': response.status_code, 'seconds': seconds,
                        'failure': body.get('code'), 'review': review, 'memory': understanding_result,
                        'evidence_count': len(body['retrieved_memory_ids']) if 'retrieved_memory_ids' in body else None,
                        'projected': providers.projected, 'draft': providers.draft, 'reply': reply,
                        'saved': len(client.get('/v1/session').json()['messages']), 'complete': complete,
                    })
                    if providers.failed or providers.blocked or not complete:
                        break
            owner.close()
        finally:
            store.engine.dispose()
    return {'model': settings.selected_model, 'max_calls': 12, 'calls': providers.calls,
            'blocked': providers.blocked, 'rows': rows, 'unexecuted': STATES[len(rows):]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    if not parser.parse_args().live:
        parser.error('--live required; at most 12 calls, one per stage per state')
    from dotenv import dotenv_values
    values = dotenv_values(ROOT / '.env')
    key = os.environ.get('GEMINI_API_KEY') or values.get('GEMINI_API_KEY')
    if not key or not key.strip():
        parser.error('Local Gemini key required')
    key = key.strip()
    model = os.environ.get('GEMINI_MODEL') or values.get('GEMINI_MODEL') or Settings.model_fields['gemini_model'].default
    settings = Settings(_env_file=None, chat_provider='gemini', gemini_api_key=key, gemini_model=model,
                        weather_provider='mock', dialogue_mode='companion', growth_enabled=True,
                        semantic_review_enabled=True, reply_review_policy='contextual',
                        memory_understanding_mode='semantic', reply_understanding_mode='semantic',
                        weather_understanding_mode='semantic', emotion_understanding_mode='semantic')
    try:
        report = run(settings, ModelMemoryUnderstanding(settings), build_provider(settings),
                     FactAnalysisProvider(settings))
    except Exception as error:
        print(f'Synthetic lifecycle interrupted: {type(error).__name__}', file=sys.stderr)
        return 2
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if key in encoded:
        return 2
    print(encoded)
    return int(bool(report['unexecuted'] or report['blocked']) or not all(r['complete'] for r in report['rows']))


if __name__ == '__main__':
    raise SystemExit(main())
