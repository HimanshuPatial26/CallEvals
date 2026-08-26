from datetime import datetime, timezone

from app import storage
from app.schemas import Agent, CallRecord


def _record(call_id: str) -> CallRecord:
    return CallRecord(
        id=call_id,
        filename="call.wav",
        dual_channel=True,
        created_at=datetime.now(timezone.utc),
        status="done",
    )


def test_save_and_load_roundtrip():
    record = _record("storage-roundtrip")
    storage.save(record)

    loaded = storage.load("storage-roundtrip")

    assert loaded is not None
    assert loaded.id == "storage-roundtrip"
    assert loaded.status == "done"


def test_save_leaves_no_tmp_file_behind():
    storage.save(_record("storage-atomic"))

    tmp_path = storage._RECORDS_DIR / "storage-atomic.json.tmp"
    assert not tmp_path.exists()


def test_load_returns_none_for_missing_call():
    assert storage.load("does-not-exist-at-all") is None


def test_load_returns_none_for_empty_file_instead_of_raising():
    (storage._RECORDS_DIR / "corrupted-empty.json").write_text("")

    assert storage.load("corrupted-empty") is None


def test_list_all_skips_a_corrupted_file_without_failing():
    storage.save(_record("good-record"))
    (storage._RECORDS_DIR / "bad-record.json").write_text("")  # e.g. a killed process mid-write

    records = storage.list_all()

    assert any(r.id == "good-record" for r in records)
    assert all(r.id != "bad-record" for r in records)


def test_list_agents_skips_a_corrupted_file():
    storage.save_agent(Agent(id="good-agent", name="Good Agent"))
    (storage._AGENTS_DIR / "bad-agent.json").write_text("{not json")

    agents = storage.list_agents()

    assert any(a.id == "good-agent" for a in agents)
    assert all(a.id != "bad-agent" for a in agents)
