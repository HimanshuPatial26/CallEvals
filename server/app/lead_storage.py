"""Filesystem-backed storage for Lead (ROADMAP.md Phase A) — same
no-database pattern as storage.py.

`set_stage` is the one write path that matters for correctness: a lead's
stage_history is the source of truth every conversion metric reads from
(see ConversionAgg's docstring in schemas.py), so it must always be
appended to, never just overwritten by a naive save of a mutated Lead.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.schemas import AssignmentEvent, FunnelStage, Lead, LeadStageEvent, LostReason

_LEADS_DIR = settings.data_dir / "leads"
_LEADS_DIR.mkdir(parents=True, exist_ok=True)


def save(lead: Lead) -> None:
    (_LEADS_DIR / f"{lead.id}.json").write_text(lead.model_dump_json(indent=2))


def load(lead_id: str) -> Lead | None:
    path = _LEADS_DIR / f"{lead_id}.json"
    if not path.exists():
        return None
    return Lead.model_validate(json.loads(path.read_text()))


def list_all() -> list[Lead]:
    leads = [Lead.model_validate(json.loads(p.read_text())) for p in _LEADS_DIR.glob("*.json")]
    return sorted(leads, key=lambda l: l.created_at, reverse=True)


def get_or_create(lead_id: str, assigned_agent_id: str | None) -> Lead:
    """Used by call upload — the caller picks the lead_id (any string they
    want, e.g. a phone number or a CRM deal ID they already track), and it's
    unique by construction: the same id reused on a later call resolves to
    the same Lead here rather than creating a duplicate. First use creates a
    placeholder Lead (display_name defaults to the id itself); a manager can
    fill in the real name/phone/source later via PATCH-equivalent calls to
    POST /api/leads/{id}/stage or by editing the record directly — there's
    no dedicated "rename a lead" endpoint yet."""
    existing = load(lead_id)
    if existing is not None:
        return existing
    lead = Lead(
        id=lead_id,
        display_name=f"Lead {lead_id}",
        assigned_agent_id=assigned_agent_id,
        created_at=datetime.now(timezone.utc),
    )
    save(lead)
    return lead


def set_stage(
    lead_id: str,
    stage: FunnelStage,
    deal_size_aed: float | None,
    changed_by: str | None,
    lost_reason: LostReason | None = None,
) -> Lead | None:
    lead = load(lead_id)
    if lead is None:
        return None
    lead.stage = stage
    if deal_size_aed is not None:
        lead.deal_size_aed = deal_size_aed
    if lost_reason is not None:
        lead.lost_reason = lost_reason
    lead.stage_history.append(LeadStageEvent(stage=stage, changed_at=datetime.now(timezone.utc), changed_by=changed_by))
    save(lead)
    return lead


def reassign(lead_id: str, assigned_agent_id: str | None, changed_by: str | None) -> Lead | None:
    """Writes the lead's current assignee and appends to assignment_history
    (ROADMAP.md C6) — same append-only audit-trail pattern as set_stage's
    stage_history, for the same reason: reports need to know *when* a lead
    was reassigned, not just who currently owns it."""
    lead = load(lead_id)
    if lead is None:
        return None
    lead.assigned_agent_id = assigned_agent_id
    lead.assignment_history.append(
        AssignmentEvent(assigned_agent_id=assigned_agent_id, changed_at=datetime.now(timezone.utc), changed_by=changed_by)
    )
    save(lead)
    return lead
