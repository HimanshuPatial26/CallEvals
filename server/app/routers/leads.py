"""Lead CRUD + stage transitions (ROADMAP.md Phase A). POST /{id}/stage
replaces the old POST /api/calls/{id}/outcome — a lead's funnel stage is
now the single source of truth for conversion, not a tag on one call.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import lead_storage, roster_storage, storage
from app.schemas import FunnelStage, Lead, LeadCallSummary, LeadDetail

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadCreate(BaseModel):
    display_name: str
    phone: str | None = None
    source: str | None = None
    assigned_agent_id: str | None = None


class LeadStageUpdate(BaseModel):
    stage: FunnelStage
    deal_size_aed: float | None = None
    changed_by: str | None = None


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


@router.post("/{lead_id}/stage")
async def set_lead_stage(lead_id: str, body: LeadStageUpdate) -> Lead:
    lead = lead_storage.set_stage(lead_id, body.stage, body.deal_size_aed, body.changed_by)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
