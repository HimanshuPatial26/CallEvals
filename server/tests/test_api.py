import io

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _valid_wav_bytes(channels: int = 1, sample_rate: int = 16000, duration_s: float = 0.1) -> bytes:
    samples = int(sample_rate * duration_s)
    data = np.zeros(samples, dtype="float32") if channels == 1 else np.zeros((samples, channels), dtype="float32")
    buffer = io.BytesIO()
    sf.write(buffer, data, sample_rate, format="WAV")
    return buffer.getvalue()


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


def test_upload_rejects_blank_lead_id():
    created = client.post("/api/agents", json={"name": "Upload Test Agent"})
    agent_id = created.json()["id"]

    response = client.post(
        "/api/calls",
        data={"agent_id": agent_id, "lead_id": "   "},
        files={"file": ("call.wav", b"fake-audio-bytes", "audio/wav")},
    )
    assert response.status_code == 400
    assert "lead_id" in response.json()["detail"]


def test_upload_auto_creates_a_new_lead_id_rather_than_rejecting_it():
    created = client.post("/api/agents", json={"name": "Auto Lead Test Agent"})
    agent_id = created.json()["id"]

    response = client.post(
        "/api/calls",
        data={"agent_id": agent_id, "lead_id": "brand-new-lead-id-12345"},
        files={"file": ("call.wav", _valid_wav_bytes(), "audio/wav")},
    )
    assert response.status_code == 202
    assert response.json()["lead_id"] == "brand-new-lead-id-12345"

    lead = client.get("/api/leads/brand-new-lead-id-12345").json()
    assert lead["id"] == "brand-new-lead-id-12345"
    assert lead["assigned_agent_id"] == agent_id


def test_upload_reuses_an_existing_lead_id_across_calls():
    created = client.post("/api/agents", json={"name": "Reuse Lead Test Agent"})
    agent_id = created.json()["id"]

    def upload():
        return client.post(
            "/api/calls",
            data={"agent_id": agent_id, "lead_id": "shared-lead-id-999"},
            files={"file": ("call.wav", _valid_wav_bytes(), "audio/wav")},
        )

    first = upload()
    second = upload()
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["lead_id"] == second.json()["lead_id"] == "shared-lead-id-999"

    leads_with_that_id = [lead for lead in client.get("/api/leads").json() if lead["id"] == "shared-lead-id-999"]
    assert len(leads_with_that_id) == 1  # not duplicated on the second upload
