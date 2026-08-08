from datetime import date

from fastapi import APIRouter, HTTPException

from app import lead_storage, roster_storage, storage
from app.agent_performance import compute_agent_performance
from app.schemas import AgentPerformanceReport

router = APIRouter(prefix="/api/agents", tags=["agents"])

# GET /api/agents (the roster listing) lives in routers/roster.py — this
# router only covers the performance rollup, to avoid two handlers on the
# same path.


@router.get("/{agent_id}/performance")
async def get_agent_performance(agent_id: str, start: date, end: date) -> AgentPerformanceReport:
    if start > end:
        raise HTTPException(status_code=400, detail="start must be on or before end")
    if roster_storage.load_agent(agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return compute_agent_performance(
        storage.list_all(),
        lead_storage.list_all(),
        roster_storage.list_agents(),
        roster_storage.list_teams(),
        agent_id,
        start,
        end,
    )
