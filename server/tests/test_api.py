from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_missing_call_returns_404():
    response = client.get("/api/calls/does-not-exist")
    assert response.status_code == 404


def test_feedback_on_missing_call_returns_404():
    response = client.post(
        "/api/calls/does-not-exist/feedback",
        json={"item_type": "next_step", "item_index": 0, "confirmed": True},
    )
    assert response.status_code == 404


def test_list_calls_returns_a_list():
    response = client.get("/api/calls")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
