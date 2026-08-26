from fastapi import APIRouter, HTTPException

from app import rollups, storage

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents() -> list[dict]:
    calls = storage.list_all()
    return [rollups.agent_summary(agent, calls) for agent in storage.list_agents()]


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    agent = storage.load_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    calls = storage.list_all()
    a_calls = rollups.agent_calls(calls, agent_id)
    all_calls_by_agent = {a.id: rollups.agent_calls(calls, a.id) for a in storage.list_agents()}
    team_trend = rollups.weekly_flag_free_rate(calls)
    rate, behaviors = rollups.behavior_improvement_rate(a_calls)

    return {
        **rollups.agent_summary(agent, calls),
        "trend": rollups.weekly_flag_free_rate(a_calls),
        "team_trend": team_trend,
        "objection_mix": rollups.objection_mix(a_calls),
        "behaviors": behaviors,
        "behavior_improvement_detail": rate,
        "call_ids": [c.id for c in sorted(a_calls, key=lambda c: c.created_at, reverse=True)],
        "coverage_by_agent": {aid: rollups.coverage(cs) for aid, cs in all_calls_by_agent.items()},
    }
