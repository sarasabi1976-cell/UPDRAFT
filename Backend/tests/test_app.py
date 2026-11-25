import pytest

from Backend import database
from Backend.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Use a temporary SQLite database so tests do not alter app.sqlite3."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "pytest.sqlite3")
    database.initialize()
    monkeypatch.setitem(app.config, "TESTING", True)
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint_returns_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "python-project"}


def test_root_serves_frontend_html(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    assert b"<!doctype html" in response.data.lower()


def test_frontend_static_css_is_served(client):
    response = client.get("/css/styles.css")

    assert response.status_code == 200
    assert response.content_type.startswith("text/css")
    assert b"--ink" in response.data


def test_unknown_api_route_returns_json_404(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.get_json() == {"error": "API route not found."}
