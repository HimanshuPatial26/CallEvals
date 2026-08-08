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
from app.schemas import FunnelStage, Lead, LeadStageEvent

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


def set_stage(lead_id: str, stage: FunnelStage, deal_size_aed: float | None, changed_by: str | None) -> Lead | None:
    lead = load(lead_id)
    if lead is None:
        return None
    lead.stage = stage
    if deal_size_aed is not None:
        lead.deal_size_aed = deal_size_aed
    lead.stage_history.append(LeadStageEvent(stage=stage, changed_at=datetime.now(timezone.utc), changed_by=changed_by))
    save(lead)
    return lead
