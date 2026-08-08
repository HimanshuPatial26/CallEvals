"""Cross-call rollup for one agent over one period — the AGENT level of the
CALL -> AGENT -> TEAM -> ORGANIZATION hierarchy (ROADMAP.md). Filters calls
down to one agent's population and hands off to the shared, population-
agnostic engine in app/performance_metrics.py, which does the actual math.
See that module's docstring for what's deliberately not modeled.

"Team" benchmarks are real teammates (ROADMAP.md Phase A's roster), not
"every other agent in the org" — that was a stand-in used before a real
Team concept existed.
"""

from datetime import date, timedelta

from app.performance_metrics import compute_performance_metrics, peer_benchmark
from app.schemas import Agent, AgentPerformanceReport, CallRecord, Lead, Team


def _in_period(record: CallRecord, agent_id: str, start: date, end: date) -> bool:
    return record.agent_id == agent_id and start <= record.created_at.date() <= end


def compute_agent_performance(
    all_records: list[CallRecord],
    all_leads: list[Lead],
    roster: list[Agent],
    teams: list[Team],
    agent_id: str,
    period_start: date,
    period_end: date,
) -> AgentPerformanceReport:
    agent = next((a for a in roster if a.id == agent_id), None)
    team = next((t for t in teams if agent and t.id == agent.team_id), None) if agent else None
    teammate_ids = {a.id for a in roster if agent and a.team_id == agent.team_id and a.id != agent_id} if agent and agent.team_id else set()
    leads_by_id = {lead.id: lead for lead in all_leads}

    records = [r for r in all_records if _in_period(r, agent_id, period_start, period_end) and r.status == "done"]
    teammate_records = [
        r for r in all_records if r.agent_id in teammate_ids and period_start <= r.created_at.date() <= period_end and r.status == "done"
    ]

    prev_end = period_start - timedelta(days=1)
    prev_start = prev_end - (period_end - period_start)
    prev_records = [r for r in all_records if _in_period(r, agent_id, prev_start, prev_end) and r.status == "done"]

    metrics = compute_performance_metrics(records, leads_by_id, period_start, period_end, prev_records, teammate_records)

    if not agent or not agent.team_id:
        metrics.notes.append("This agent has no team assigned yet — team benchmarks will populate once they're placed on a team.")
    elif not teammate_records:
        metrics.notes.append("No teammates have calls in this period yet — team benchmarks will populate once they do.")
    if metrics.conversion.leads_touched == 0:
        metrics.notes.append("No leads were attributed to this agent's calls in this period.")
    elif metrics.conversion.leads_tagged == 0:
        metrics.notes.append(
            "None of this agent's leads have a stage set yet — conversion/funnel/revenue metrics need at least one "
            "tag via POST /api/leads/{id}/stage."
        )

    team_benchmark = peer_benchmark(
        metrics.avg_call_score,
        metrics.talk_time,
        metrics.conversion,
        metrics.compliance_score_pct,
        teammate_records,
        leads_by_id,
        period_start,
        period_end,
        comparison_label="Team average",
    )

    return AgentPerformanceReport(
        **metrics.model_dump(),
        agent_id=agent_id,
        agent_name=agent.name if agent else agent_id,
        team_id=team.id if team else None,
        team_name=team.name if team else None,
        team_benchmark=team_benchmark,
    )
