from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import rollups, storage

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("")
async def list_leads() -> list[dict]:
    calls = storage.list_all()
    out = []
    for lead in storage.list_leads():
        lead_calls = [c for c in calls if c.lead_id == lead.id]
        latest_done = sorted((c for c in lead_calls if c.status == "done"), key=lambda c: c.created_at, reverse=True)
        out.append(
            {
                **lead.model_dump(),
                "call_count": len(lead_calls),
                "open_next_step": rollups.lead_open_next_step(calls, lead.id),
                "objection_tags": rollups.lead_objection_tags(calls, lead.id),
                "last_call_at": latest_done[0].created_at if latest_done else None,
            }
        )
    return out


@router.get("/{lead_id}")
async def get_lead(lead_id: str) -> dict:
    lead = storage.load_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    calls = storage.list_all()
    lead_calls = sorted((c for c in calls if c.lead_id == lead_id), key=lambda c: c.created_at, reverse=True)
    return {
        **lead.model_dump(),
        "open_next_step": rollups.lead_open_next_step(calls, lead_id),
        "objection_tags": rollups.lead_objection_tags(calls, lead_id),
        "calls": [
            {
                "id": c.id,
                "filename": c.filename,
                "status": c.status,
                "created_at": c.created_at,
                "duration": c.duration,
                "summary": c.extraction.summary if c.extraction else None,
            }
            for c in lead_calls
        ],
    }


class LeadUpdate(BaseModel):
    stage: str | None = None
    unit: str | None = None
    budget: str | None = None
    source: str | None = None


@router.patch("/{lead_id}")
async def update_lead(lead_id: str, update: LeadUpdate) -> dict:
    lead = storage.load_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    data = update.model_dump(exclude_unset=True)
    updated = lead.model_copy(update=data)
    storage.save_lead(updated)
    return updated.model_dump()
