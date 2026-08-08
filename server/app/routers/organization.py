from datetime import date

from fastapi import APIRouter, HTTPException

from app import lead_storage, roster_storage, storage
from app.org_performance import compute_org_performance
from app.schemas import OrgPerformanceReport

router = APIRouter(prefix="/api/organization", tags=["organization"])


@router.get("/performance")
async def get_org_performance(start: date, end: date) -> OrgPerformanceReport:
    if start > end:
        raise HTTPException(status_code=400, detail="start must be on or before end")
    return compute_org_performance(
        storage.list_all(), lead_storage.list_all(), roster_storage.list_agents(), roster_storage.list_teams(), start, end
    )
