import json
from datetime import datetime, timezone

from app import storage
from app.schemas import CallRecord


def _new_record(call_id: str) -> CallRecord:
    return CallRecord(
        id=call_id,
        filename="call.wav",
        dual_channel=False,
        created_at=datetime.now(timezone.utc),
        agent_id="agent-1",
        lead_id="lead-1",
        status="done",
    )


def test_list_all_returns_valid_records():
    storage.save(_new_record("call-a"))
    storage.save(_new_record("call-b"))
    ids = {r.id for r in storage.list_all()}
    assert {"call-a", "call-b"} <= ids


def test_list_all_skips_unreadable_record_instead_of_raising(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_RECORDS_DIR", tmp_path)
    (tmp_path / "not-json.json").write_text("{not valid json")

    result = storage.list_all()
    assert result == []


def test_list_all_skips_pre_phase_a_record_missing_agent_id_and_lead_id(tmp_path, monkeypatch):
    """Regression test for the real failure a user hit in production: a
    CallRecord saved before agent_id/lead_id existed used to 500 the whole
    GET /api/calls endpoint. It should be skipped, not crash the request."""
    monkeypatch.setattr(storage, "_RECORDS_DIR", tmp_path)
    legacy = {
        "id": "legacy-1",
        "filename": "call_1.wav",
        "dual_channel": True,
        "created_at": "2026-08-01T10:00:00Z",
        "agent_name": "Rahul Sharma",
        "transcript": [],
        "extraction": None,
        "insights": None,
        "compliance": None,
        "overall_score": None,
        "outcome": {"stage": "won", "deal_size_aed": 450000.0},
        "feedback": [],
        "status": "done",
        "error": None,
    }
    (tmp_path / "legacy-1.json").write_text(json.dumps(legacy))

    result = storage.list_all()
    assert result == []
