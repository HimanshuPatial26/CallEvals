from fastapi import APIRouter

from app import rollups, storage

router = APIRouter(prefix="/api/org", tags=["org"])


@router.get("")
async def get_org_rollup() -> dict:
    calls = storage.list_all()
    agents = storage.list_agents()
    leads = storage.list_leads()
    rubric = storage.load_settings()
    behavior_rate, _ = rollups.behavior_improvement_rate(calls)

    return {
        "coverage": rollups.coverage(calls),
        "extraction_precision": rollups.extraction_precision(calls),
        "manager_engagement": rollups.manager_engagement(calls),
        "behavior_improvement": behavior_rate,
        "roster": [rollups.agent_summary(a, calls) for a in agents],
        "where_deals_stall": rollups.where_deals_stall(calls, leads),
        "disclosure_detected_pct": round(
            100.0
            * sum(1 for c in calls if c.status == "done" and c.flags and not c.flags.missing_disclosure)
            / max(1, sum(1 for c in calls if c.status == "done" and c.flags)),
            1,
        ),
        "retention_days": rubric.retention_days,
        "rep_private_mode": rubric.rep_private_mode,
        "call_count": len(calls),
        "agent_count": len(agents),
        "lead_count": len(leads),
    }
