from app.org_performance import compute_org_performance
from tests.factories import OMAR, PERIOD_END, PERIOD_START, RAHUL, SARA, TEAM_A, TEAM_B, make_call, make_lead


def test_empty_org_returns_graceful_nones_not_errors():
    report = compute_org_performance([], [], [], [], PERIOD_START, PERIOD_END)
    assert report.calls_analyzed == 0
    assert report.avg_call_score is None
    assert report.team_leaderboard == []


def test_no_teams_gets_explicit_note():
    report = compute_org_performance([], [], [], [], PERIOD_START, PERIOD_END)
    assert any("No teams exist" in n for n in report.notes)


def test_org_pools_every_team_no_filtering():
    lead = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0),
        make_call("c2", "agent-sara", "lead-1", 1, score_mult=0.5),
        make_call("c3", "agent-omar", "lead-1", 1, score_mult=0.1),
    ]
    report = compute_org_performance(records, [lead], [RAHUL, SARA, OMAR], [TEAM_A, TEAM_B], PERIOD_START, PERIOD_END)
    assert report.calls_analyzed == 3
    assert report.avg_call_score == 55.7


def test_org_has_no_peer_benchmark_field_at_all():
    # OrgPerformanceReport doesn't carry a benchmark-vs-peer field the way
    # Agent/Team reports do -- there's no peer to compare an org against.
    report = compute_org_performance([], [], [], [], PERIOD_START, PERIOD_END)
    assert not hasattr(report, "team_benchmark")
    assert not hasattr(report, "org_benchmark")


def test_team_leaderboard_sorts_best_first_and_matches_team_performance():
    lead = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0),
        make_call("c2", "agent-sara", "lead-1", 1, score_mult=0.5),
        make_call("c3", "agent-omar", "lead-1", 1, score_mult=0.1),
    ]
    roster, teams = [RAHUL, SARA, OMAR], [TEAM_A, TEAM_B]
    report = compute_org_performance(records, [lead], roster, teams, PERIOD_START, PERIOD_END)
    assert [row.id for row in report.team_leaderboard] == ["team-1", "team-2"]
    assert report.team_leaderboard[0].overall_score == 76.2
    assert report.team_leaderboard[1].overall_score == 14.5


def test_team_leaderboard_puts_teams_with_no_calls_last_not_omitted():
    lead = make_lead("lead-1")
    records = [make_call("c1", "agent-rahul", "lead-1", 1)]
    report = compute_org_performance(records, [lead], [RAHUL], [TEAM_A, TEAM_B], PERIOD_START, PERIOD_END)
    assert [row.id for row in report.team_leaderboard] == ["team-1", "team-2"]
    assert report.team_leaderboard[1].overall_score is None
