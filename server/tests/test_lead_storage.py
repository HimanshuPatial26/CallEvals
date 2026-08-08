from datetime import datetime, timezone

from app import lead_storage
from app.schemas import FunnelStage, Lead


def _new_lead(lead_id: str) -> Lead:
    return Lead(id=lead_id, display_name="Ahmed - 2BR Marina", created_at=datetime.now(timezone.utc))


def test_lead_round_trips():
    lead = _new_lead("lead-1")
    lead_storage.save(lead)
    assert lead_storage.load("lead-1") == lead


def test_load_missing_lead_returns_none():
    assert lead_storage.load("no-such-lead") is None


def test_set_stage_appends_history_rather_than_overwriting():
    lead_storage.save(_new_lead("lead-2"))

    updated = lead_storage.set_stage("lead-2", FunnelStage.QUALIFIED, None, "agent-1")
    assert updated.stage == FunnelStage.QUALIFIED
    assert len(updated.stage_history) == 1

    updated = lead_storage.set_stage("lead-2", FunnelStage.WON, 500000.0, "agent-1")
    assert updated.stage == FunnelStage.WON
    assert updated.deal_size_aed == 500000.0
    assert len(updated.stage_history) == 2
    assert [e.stage for e in updated.stage_history] == [FunnelStage.QUALIFIED, FunnelStage.WON]


def test_set_stage_on_missing_lead_returns_none():
    assert lead_storage.set_stage("no-such-lead", FunnelStage.WON, None, None) is None


def test_set_stage_without_deal_size_keeps_existing_value():
    lead_storage.save(_new_lead("lead-3"))
    lead_storage.set_stage("lead-3", FunnelStage.WON, 250000.0, None)

    updated = lead_storage.set_stage("lead-3", FunnelStage.WON, None, None)
    assert updated.deal_size_aed == 250000.0


def test_get_or_create_creates_a_new_lead_with_the_given_id():
    lead = lead_storage.get_or_create("phone-971500000000", assigned_agent_id="agent-1")
    assert lead.id == "phone-971500000000"
    assert lead.assigned_agent_id == "agent-1"
    assert lead_storage.load("phone-971500000000") == lead


def test_get_or_create_returns_the_existing_lead_without_duplicating():
    original = lead_storage.get_or_create("shared-id", assigned_agent_id="agent-1")
    original_stage_history_len = len(original.stage_history)

    lead_storage.set_stage("shared-id", FunnelStage.QUALIFIED, None, "agent-1")
    reused = lead_storage.get_or_create("shared-id", assigned_agent_id="agent-2")

    assert reused.id == original.id
    assert reused.stage == FunnelStage.QUALIFIED  # reflects the stage change, not a fresh record
    assert len(reused.stage_history) == original_stage_history_len + 1
