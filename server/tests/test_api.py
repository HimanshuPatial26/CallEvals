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


def test_outcome_on_missing_call_returns_404():
    response = client.post("/api/calls/does-not-exist/outcome", json={"stage": "won", "deal_size_aed": 500000})
    assert response.status_code == 404


def test_list_agents_returns_a_list():
    response = client.get("/api/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_agent_performance_for_unknown_agent_returns_empty_report_not_error():
    response = client.get(
        "/api/agents/Nobody-At-All/performance", params={"start": "2026-08-01", "end": "2026-08-31"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent_name"] == "Nobody-At-All"
    assert body["calls_analyzed"] == 0


def test_agent_performance_rejects_inverted_date_range():
    response = client.get(
        "/api/agents/Nobody-At-All/performance", params={"start": "2026-08-31", "end": "2026-08-01"}
    )
    assert response.status_code == 400
