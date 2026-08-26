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


def test_get_missing_call_audio_returns_404():
    response = client.get("/api/calls/does-not-exist/audio")
    assert response.status_code == 404


def test_list_agents_returns_a_list():
    response = client.get("/api/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_missing_agent_returns_404():
    response = client.get("/api/agents/does-not-exist")
    assert response.status_code == 404


def test_list_leads_returns_a_list():
    response = client.get("/api/leads")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_missing_lead_returns_404():
    response = client.get("/api/leads/does-not-exist")
    assert response.status_code == 404


def test_org_rollup_returns_expected_shape():
    response = client.get("/api/org")
    assert response.status_code == 200
    body = response.json()
    assert "coverage" in body
    assert "roster" in body


def test_settings_roundtrip():
    get_response = client.get("/api/settings")
    assert get_response.status_code == 200
    rubric = get_response.json()
    rubric["digest"] = "Weekly"

    put_response = client.put("/api/settings", json=rubric)
    assert put_response.status_code == 200
    assert put_response.json()["digest"] == "Weekly"

    confirm = client.get("/api/settings")
    assert confirm.json()["digest"] == "Weekly"
