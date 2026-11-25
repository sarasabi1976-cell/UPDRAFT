import pytest

from Backend import database
from Backend.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "pytest.sqlite3")
    database.initialize()
    monkeypatch.setitem(app.config, "TESTING", True)

    with app.test_client() as test_client:
        yield test_client


def test_health_returns_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "service": "python-project",
    }


def test_career_options_returns_degrees_and_skills(client):
    response = client.get("/api/career/options")

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["degrees"], list)
    assert isinstance(data["skills"], list)


def test_warmups_returns_prompts(client):
    response = client.get("/api/practice/warmups")

    assert response.status_code == 200
    assert isinstance(response.get_json()["prompts"], list)


def test_questions_returns_a_list(client):
    response = client.get("/api/practice/questions")

    assert response.status_code == 200
    assert isinstance(response.get_json()["questions"], list)


def test_invalid_focus_session_is_rejected(client):
    response = client.post(
        "/api/practice/focus-sessions",
        json={
            "durationSeconds": 0,
            "promptId": None,
            "completed": False,
        },
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_unknown_api_route_returns_404(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.get_json() == {"error": "API route not found."}