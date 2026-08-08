"""Lead CRUD + stage transitions (ROADMAP.md Phase A). POST /{id}/stage
replaces the old POST /api/calls/{id}/outcome — a lead's funnel stage is
now the single source of truth for conversion, not a tag on one call.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import lead_storage, roster_storage, storage
from app.schemas import FunnelStage, Lead, LeadCallSummary, LeadDetail, LostReason

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadCreate(BaseModel):
    display_name: str
    phone: str | None = None
    source: str | None = None
    assigned_agent_id: str | None = None


class LeadStageUpdate(BaseModel):
    stage: FunnelStage
    deal_size_aed: float | None = None
    lost_reason: LostReason | None = None
    changed_by: str | None = None


class LeadReassign(BaseModel):
    assigned_agent_id: str | None = None
    changed_by: str | None = None


class LeadUpdate(BaseModel):
    display_name: str | None = None
    phone: str | None = None
    source: str | None = None


@router.post("", status_code=201)
async def create_lead(body: LeadCreate) -> Lead:
    if body.assigned_agent_id and roster_storage.load_agent(body.assigned_agent_id) is None:
        raise HTTPException(status_code=400, detail=f"assigned_agent_id {body.assigned_agent_id!r} does not exist")
    if not body.display_name.strip():
        raise HTTPException(status_code=400, detail="display_name is required")
    lead = Lead(
        id=str(uuid.uuid4()),
        display_name=body.display_name.strip(),
        phone=body.phone,
        source=body.source,
        assigned_agent_id=body.assigned_agent_id,
        created_at=datetime.now(timezone.utc),
    )
    lead_storage.save(lead)
    return lead


@router.get("")
async def list_leads(assigned_agent_id: str | None = None, stage: FunnelStage | None = None, q: str | None = None) -> list[Lead]:
    leads = lead_storage.list_all()
    if assigned_agent_id:
        leads = [lead for lead in leads if lead.assigned_agent_id == assigned_agent_id]
    if stage:
        leads = [lead for lead in leads if lead.stage == stage]
    if q:
        needle = q.lower()
        leads = [lead for lead in leads if needle in lead.display_name.lower() or (lead.phone and needle in lead.phone)]
    return leads


@router.get("/{lead_id}")
async def get_lead(lead_id: str) -> LeadDetail:
    lead = lead_storage.load(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    calls = [
        LeadCallSummary(id=r.id, created_at=r.created_at, agent_id=r.agent_id, overall_score=r.overall_score, status=r.status)
        for r in storage.list_all()
        if r.lead_id == lead_id
    ]
    return LeadDetail(**lead.model_dump(), calls=calls)


@router.patch("/{lead_id}")
async def update_lead(lead_id: str, body: LeadUpdate) -> Lead:
    """Edits display_name/phone/source — the fields get_or_create's
    docstring always said would need a real edit path once one existed
    (auto-provisioned leads default to display_name="Lead {id}" and no
    source; C4's source-conversion breakdown made "no way to ever set
    source after creation" a real gap, not just a cosmetic one)."""
    lead = lead_storage.load(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    if body.display_name is not None and not body.display_name.strip():
        raise HTTPException(status_code=400, detail="display_name cannot be blank")
    update_data = body.model_dump(exclude_unset=True)
    if "display_name" in update_data:
        update_data["display_name"] = update_data["display_name"].strip()
    updated = lead.model_copy(update=update_data)
    lead_storage.save(updated)
    return updated


@router.post("/{lead_id}/stage")
async def set_lead_stage(lead_id: str, body: LeadStageUpdate) -> Lead:
    lead = lead_storage.set_stage(lead_id, body.stage, body.deal_size_aed, body.changed_by, body.lost_reason)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/{lead_id}/reassign")
async def reassign_lead(lead_id: str, body: LeadReassign) -> Lead:
    if body.assigned_agent_id and roster_storage.load_agent(body.assigned_agent_id) is None:
        raise HTTPException(status_code=400, detail=f"assigned_agent_id {body.assigned_agent_id!r} does not exist")
    lead = lead_storage.reassign(lead_id, body.assigned_agent_id, body.changed_by)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
