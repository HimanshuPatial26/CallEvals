import json

from app import lead_storage, roster_storage, storage
from app.schemas import FunnelStage
from scripts import migrate_legacy_calls


def _isolate(tmp_path, monkeypatch):
    """Point every storage module's directory at a fresh tmp_path, rather
    than the shared session-wide temp dir from conftest.py — avoids
    cross-test collisions on agent names like "Rahul Sharma" that other
    test files also use."""
    monkeypatch.setattr(storage, "_RECORDS_DIR", tmp_path)
    monkeypatch.setattr(migrate_legacy_calls, "_RECORDS_DIR", tmp_path)
    monkeypatch.setattr(roster_storage, "_AGENTS_DIR", tmp_path / "agents")
    monkeypatch.setattr(roster_storage, "_TEAMS_DIR", tmp_path / "teams")
    monkeypatch.setattr(lead_storage, "_LEADS_DIR", tmp_path / "leads")
    (tmp_path / "agents").mkdir()
    (tmp_path / "teams").mkdir()
    (tmp_path / "leads").mkdir()


def _write_legacy_record(tmp_path, call_id: str, agent_name: str, outcome: dict | None) -> None:
    record = {
        "id": call_id,
        "filename": f"{call_id}.wav",
        "dual_channel": True,
        "created_at": "2026-08-01T10:00:00Z",
        "agent_name": agent_name,
        "transcript": [],
        "extraction": None,
        "insights": None,
        "compliance": None,
        "overall_score": None,
        "outcome": outcome,
        "feedback": [],
        "status": "done",
        "error": None,
    }
    (tmp_path / f"{call_id}.json").write_text(json.dumps(record))


def test_migrate_backfills_agent_id_lead_id_and_preserves_outcome(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _write_legacy_record(tmp_path, "legacy-1", "Migration Test Agent", {"stage": "won", "deal_size_aed": 450000.0})

    assert storage.list_all() == []  # unreadable pre-migration, per storage.py's resilience fix

    migrate_legacy_calls.migrate()

    records = storage.list_all()
    assert len(records) == 1
    record = records[0]

    agent = roster_storage.load_agent(record.agent_id)
    assert agent.name == "Migration Test Agent"

    lead = lead_storage.load(record.lead_id)
    assert lead.stage == FunnelStage.WON
    assert lead.deal_size_aed == 450000.0
    assert len(lead.stage_history) == 1


def test_migrate_dedupes_agent_by_name_across_multiple_legacy_calls(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _write_legacy_record(tmp_path, "legacy-1", "Shared Agent", None)
    _write_legacy_record(tmp_path, "legacy-2", "Shared Agent", None)

    migrate_legacy_calls.migrate()

    records = {r.id: r for r in storage.list_all()}
    assert records["legacy-1"].agent_id == records["legacy-2"].agent_id
    assert len(roster_storage.list_agents()) == 1
    # but each call still gets its own lead -- no way to know they're the same prospect
    assert records["legacy-1"].lead_id != records["legacy-2"].lead_id


def test_migrate_defaults_untagged_outcome_to_no_stage_history(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _write_legacy_record(tmp_path, "legacy-1", "Untagged Agent", None)

    migrate_legacy_calls.migrate()

    record = storage.list_all()[0]
    lead = lead_storage.load(record.lead_id)
    assert lead.stage == FunnelStage.UNTAGGED
    assert lead.stage_history == []


def test_migrate_is_idempotent(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    _write_legacy_record(tmp_path, "legacy-1", "Idempotency Agent", {"stage": "qualified"})

    migrate_legacy_calls.migrate()
    first_pass = storage.list_all()[0]

    migrate_legacy_calls.migrate()
    second_pass = storage.list_all()[0]

    assert first_pass.agent_id == second_pass.agent_id
    assert first_pass.lead_id == second_pass.lead_id
    assert len(roster_storage.list_agents()) == 1
    assert len(lead_storage.list_all()) == 1


def test_migrate_leaves_already_current_records_untouched(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    current_record = {
        "id": "current-1",
        "filename": "current.wav",
        "dual_channel": True,
        "created_at": "2026-08-01T10:00:00Z",
        "agent_id": "agent-already-real",
        "lead_id": "lead-already-real",
        "transcript": [],
        "extraction": None,
        "insights": None,
        "compliance": None,
        "overall_score": None,
        "feedback": [],
        "status": "done",
        "error": None,
    }
    (tmp_path / "current-1.json").write_text(json.dumps(current_record))

    migrate_legacy_calls.migrate()

    record = storage.list_all()[0]
    assert record.agent_id == "agent-already-real"
    assert record.lead_id == "lead-already-real"
    assert roster_storage.list_agents() == []  # migration shouldn't invent an agent for an already-current record
