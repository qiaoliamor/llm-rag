"""All tests default to disposable storage, never the user's .env/database."""
import os
import tempfile
import pytest

_test_database = tempfile.TemporaryDirectory(prefix='persona-tests-')
# Historical audit suites remain pinned; companion behavior is tested explicitly.
os.environ['MEMORY_UNDERSTANDING_MODE'] = 'legacy'  # Pin historical contracts; semantic suites opt in explicitly.
os.environ['WEATHER_UNDERSTANDING_MODE'] = 'legacy'  # Explicit historical weather replay, never a runtime fallback.
os.environ['DIALOGUE_MODE'] = 'audit'
os.environ['GROWTH_ENABLED'] = 'false'  # Historical capability suites; growth has explicit tests.
os.environ['MEMORY_DATABASE_URL'] = 'sqlite:///' + _test_database.name + '/bootstrap.sqlite3'


@pytest.fixture(autouse=True)
def isolated_memory_database(monkeypatch, tmp_path):
    monkeypatch.setenv('MEMORY_DATABASE_URL', 'sqlite:///' + str(tmp_path / 'memory.sqlite3'))
