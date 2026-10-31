"""Ensure React build output is usable through the unchanged FastAPI routes."""
import re
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def test_built_frontend_assets_are_served_under_existing_csp():
    client = TestClient(create_app(Settings(_env_file=None, chat_provider='mock')))
    page = client.get('/')
    assert page.status_code == 200, 'Run npm run build --prefix frontend before pytest'
    assert 'id="root"' in page.text
    resources = re.findall(r'(?:src|href)="(/static/assets/[^\"]+)"', page.text)
    assert any(url.endswith('.js') for url in resources)
    assert any(url.endswith('.css') for url in resources)
    for url in resources:
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.content) > 0
    assert "script-src 'self'" in page.headers['content-security-policy']
    assert 'unsafe-eval' not in page.headers['content-security-policy']
    assert client.get('/frontend/src/App.tsx').status_code == 404
