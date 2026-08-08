"""Cross-call rollup for the whole organization over one period — the
ORGANIZATION level of the CALL -> AGENT -> TEAM -> ORGANIZATION hierarchy
(ROADMAP.md Phase B). No filtering by agent or team — every call in the
period — and no peer group to benchmark against (there's one org; no
Organization entity exists to compare it to another, and none is needed
for this pass — see ROADMAP.md Phase A's note on why).
"""

from datetime import date, timedelta

from app.performance_metrics import compute_performance_metrics
from app.schemas import Agent, CallRecord, Lead, LeaderboardRow, OrgPerformanceReport, Team
from app.team_performance import compute_team_performance


def compute_org_performance(
    all_records: list[CallRecord],
    all_leads: list[Lead],
    roster: list[Agent],
    teams: list[Team],
    period_start: date,
    period_end: date,
) -> OrgPerformanceReport:
    leads_by_id = {lead.id: lead for lead in all_leads}

    records = [r for r in all_records if period_start <= r.created_at.date() <= period_end and r.status == "done"]

    prev_end = period_start - timedelta(days=1)
    prev_start = prev_end - (period_end - period_start)
    prev_records = [r for r in all_records if prev_start <= r.created_at.date() <= prev_end and r.status == "done"]

    metrics = compute_performance_metrics(records, leads_by_id, period_start, period_end, prev_records, [], subject="the org")

    if not teams:
        metrics.notes.append("No teams exist in the roster yet.")
    if metrics.conversion.leads_touched == 0:
        metrics.notes.append("No leads were attributed to any call in this period.")
    elif metrics.conversion.leads_tagged == 0:
        metrics.notes.append(
            "No leads have a stage set yet — conversion/funnel/revenue metrics need at least one tag via "
            "POST /api/leads/{id}/stage."
        )

    team_leaderboard = _team_leaderboard(all_records, all_leads, roster, teams, period_start, period_end)

    return OrgPerformanceReport(**metrics.model_dump(), team_leaderboard=team_leaderboard)


def _team_leaderboard(
    all_records: list[CallRecord],
    all_leads: list[Lead],
    roster: list[Agent],
    teams: list[Team],
    period_start: date,
    period_end: date,
) -> list[LeaderboardRow]:
    rows = []
    for team in teams:
        report = compute_team_performance(all_records, all_leads, roster, teams, team.id, period_start, period_end)
        rows.append(
            LeaderboardRow(
                id=team.id,
                name=team.name,
                overall_score=report.avg_call_score,
                conversion_rate_pct=report.conversion.conversion_rate_pct,
                calls_analyzed=report.calls_analyzed,
            )
        )
    # best-performing teams first; teams with no scored calls yet sort last rather than being omitted
    rows.sort(key=lambda row: (row.overall_score is None, -(row.overall_score or 0)))
    return rows
