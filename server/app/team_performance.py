"""Cross-call rollup for one team over one period — the TEAM level of the
CALL -> AGENT -> TEAM -> ORGANIZATION hierarchy (ROADMAP.md Phase B).
Filters calls down to the team's roster and hands off to the shared engine
in app/performance_metrics.py, same pattern as app/agent_performance.py one
level up. The peer group for team-level benchmarking is every other team in
the org, not individual agents.
"""

from datetime import date, timedelta

from app.agent_performance import compute_agent_performance
from app.performance_metrics import compute_performance_metrics, peer_benchmark
from app.schemas import Agent, CallRecord, Lead, LeaderboardRow, Team, TeamPerformanceReport


def _team_agent_ids(roster: list[Agent], team_id: str) -> set[str]:
    return {a.id for a in roster if a.team_id == team_id}


def _in_period(record: CallRecord, agent_ids: set[str], start: date, end: date) -> bool:
    return record.agent_id in agent_ids and start <= record.created_at.date() <= end


def compute_team_performance(
    all_records: list[CallRecord],
    all_leads: list[Lead],
    roster: list[Agent],
    teams: list[Team],
    team_id: str,
    period_start: date,
    period_end: date,
) -> TeamPerformanceReport:
    team = next((t for t in teams if t.id == team_id), None)
    team_agent_ids = _team_agent_ids(roster, team_id)
    other_team_agent_ids = {a.id for a in roster if a.team_id and a.team_id != team_id}
    leads_by_id = {lead.id: lead for lead in all_leads}

    records = [r for r in all_records if _in_period(r, team_agent_ids, period_start, period_end) and r.status == "done"]
    other_team_records = [
        r for r in all_records if _in_period(r, other_team_agent_ids, period_start, period_end) and r.status == "done"
    ]

    prev_end = period_start - timedelta(days=1)
    prev_start = prev_end - (period_end - period_start)
    prev_records = [r for r in all_records if _in_period(r, team_agent_ids, prev_start, prev_end) and r.status == "done"]

    metrics = compute_performance_metrics(
        records, leads_by_id, period_start, period_end, prev_records, other_team_records, subject="the team"
    )

    if not team_agent_ids:
        metrics.notes.append("This team has no agents assigned yet.")
    if not other_team_records:
        metrics.notes.append("No other teams have calls in this period yet — org benchmarks will populate once they do.")
    if metrics.conversion.leads_touched == 0:
        metrics.notes.append("No leads were attributed to this team's calls in this period.")
    elif metrics.conversion.leads_tagged == 0:
        metrics.notes.append(
            "None of this team's leads have a stage set yet — conversion/funnel/revenue metrics need at least one "
            "tag via POST /api/leads/{id}/stage."
        )

    agent_leaderboard = _agent_leaderboard(all_records, all_leads, roster, teams, team_agent_ids, period_start, period_end)

    org_benchmark = peer_benchmark(
        metrics.avg_call_score,
        metrics.talk_time,
        metrics.conversion,
        metrics.compliance_score_pct,
        other_team_records,
        leads_by_id,
        period_start,
        period_end,
        comparison_label="Org average",
    )

    manager_name = next((a.name for a in roster if team and a.id == team.manager_agent_id), None)

    return TeamPerformanceReport(
        **metrics.model_dump(),
        team_id=team_id,
        team_name=team.name if team else team_id,
        manager_agent_id=team.manager_agent_id if team else None,
        manager_name=manager_name,
        agent_leaderboard=agent_leaderboard,
        org_benchmark=org_benchmark,
    )


def _agent_leaderboard(
    all_records: list[CallRecord],
    all_leads: list[Lead],
    roster: list[Agent],
    teams: list[Team],
    team_agent_ids: set[str],
    period_start: date,
    period_end: date,
) -> list[LeaderboardRow]:
    rows = []
    for agent_id in team_agent_ids:
        agent = next(a for a in roster if a.id == agent_id)
        report = compute_agent_performance(all_records, all_leads, roster, teams, agent_id, period_start, period_end)
        rows.append(
            LeaderboardRow(
                id=agent.id,
                name=agent.name,
                overall_score=report.avg_call_score,
                conversion_rate_pct=report.conversion.conversion_rate_pct,
                calls_analyzed=report.calls_analyzed,
            )
        )
    # best performers first; agents with no scored calls yet sort last rather than being omitted
    rows.sort(key=lambda row: (row.overall_score is None, -(row.overall_score or 0)))
    return rows
