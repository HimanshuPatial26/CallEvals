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


def test_stage_update_on_missing_lead_returns_404():
    response = client.post("/api/leads/does-not-exist/stage", json={"stage": "won", "deal_size_aed": 500000})
    assert response.status_code == 404


def test_list_agents_returns_a_list():
    response = client.get("/api/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_agent_performance_for_unknown_agent_returns_404():
    response = client.get(
        "/api/agents/does-not-exist/performance", params={"start": "2026-08-01", "end": "2026-08-31"}
    )
    assert response.status_code == 404


def test_agent_performance_for_real_agent_with_no_calls_returns_empty_report():
    created = client.post("/api/agents", json={"name": "Test Agent"})
    agent_id = created.json()["id"]

    response = client.get(f"/api/agents/{agent_id}/performance", params={"start": "2026-08-01", "end": "2026-08-31"})
    assert response.status_code == 200
    body = response.json()
    assert body["agent_id"] == agent_id
    assert body["agent_name"] == "Test Agent"
    assert body["calls_analyzed"] == 0


def test_agent_performance_rejects_inverted_date_range():
    response = client.get(
        "/api/agents/does-not-exist/performance", params={"start": "2026-08-31", "end": "2026-08-01"}
    )
    assert response.status_code == 400


def test_upload_rejects_unknown_agent_id():
    response = client.post(
        "/api/calls",
        data={"agent_id": "does-not-exist", "lead_id": "also-does-not-exist"},
        files={"file": ("call.wav", b"fake-audio-bytes", "audio/wav")},
    )
    assert response.status_code == 400
    assert "agent_id" in response.json()["detail"]


def test_upload_rejects_unknown_lead_id():
    created = client.post("/api/agents", json={"name": "Upload Test Agent"})
    agent_id = created.json()["id"]

    response = client.post(
        "/api/calls",
        data={"agent_id": agent_id, "lead_id": "does-not-exist"},
        files={"file": ("call.wav", b"fake-audio-bytes", "audio/wav")},
    )
    assert response.status_code == 400
    assert "lead_id" in response.json()["detail"]
