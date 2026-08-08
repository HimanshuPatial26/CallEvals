from datetime import date

from fastapi import APIRouter, HTTPException

from app import storage
from app.agent_performance import compute_agent_performance
from app.schemas import AgentPerformanceReport

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents() -> list[dict]:
    """Distinct agent names with a calls-analyzed count, for a picker —
    derived from whatever calls have been uploaded, not a roster the app
    manages."""
    records = [r for r in storage.list_all() if r.status == "done"]
    counts: dict[str, int] = {}
    for r in records:
        counts[r.agent_name] = counts.get(r.agent_name, 0) + 1
    return [{"agent_name": name, "calls_analyzed": count} for name, count in sorted(counts.items())]


@router.get("/{agent_name}/performance")
async def get_agent_performance(agent_name: str, start: date, end: date) -> AgentPerformanceReport:
    if start > end:
        raise HTTPException(status_code=400, detail="start must be on or before end")
    return compute_agent_performance(storage.list_all(), agent_name, start, end)
