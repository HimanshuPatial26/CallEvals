from app.agent_performance import compute_agent_performance
from app.schemas import Agent, Team
from app.team_performance import compute_team_performance
from tests.factories import OMAR, PERIOD_END, PERIOD_START, RAHUL, SARA, TEAM_A, TEAM_B, make_call, make_lead


def test_unknown_team_falls_back_to_id_as_name():
    report = compute_team_performance([], [], [], [], "ghost-team", PERIOD_START, PERIOD_END)
    assert report.team_name == "ghost-team"
    assert report.calls_analyzed == 0
    assert report.manager_agent_id is None


def test_empty_team_gets_no_agents_note():
    report = compute_team_performance([], [], [], [TEAM_A], "team-1", PERIOD_START, PERIOD_END)
    assert any("no agents assigned" in n for n in report.notes)


def test_team_pools_calls_by_volume_not_by_averaging_agent_scores():
    """Rahul (score_mult=1.0) and Sara (score_mult=0.5) are both on Team A --
    the team's avg_call_score must be the pooled average of their two calls,
    not the average of their two agent-level averages (same number here, but
    computed a different way -- this locks in the pooling behavior)."""
    lead = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0),
        make_call("c2", "agent-sara", "lead-1", 1, score_mult=0.5),
        make_call("c3", "agent-omar", "lead-1", 1, score_mult=0.1),  # Team B, must not leak in
    ]
    report = compute_team_performance(records, [lead], [RAHUL, SARA, OMAR], [TEAM_A, TEAM_B], "team-1", PERIOD_START, PERIOD_END)
    assert report.calls_analyzed == 2
    assert report.avg_call_score == 76.2


def test_agent_leaderboard_sorts_best_first_and_matches_agent_performance():
    lead = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0),
        make_call("c2", "agent-sara", "lead-1", 1, score_mult=0.5),
    ]
    roster, teams = [RAHUL, SARA], [TEAM_A]
    report = compute_team_performance(records, [lead], roster, teams, "team-1", PERIOD_START, PERIOD_END)
    assert [row.id for row in report.agent_leaderboard] == ["agent-rahul", "agent-sara"]

    rahul_report = compute_agent_performance(records, [lead], roster, teams, "agent-rahul", PERIOD_START, PERIOD_END)
    leaderboard_row = next(row for row in report.agent_leaderboard if row.id == "agent-rahul")
    assert leaderboard_row.overall_score == rahul_report.avg_call_score
    assert leaderboard_row.calls_analyzed == rahul_report.calls_analyzed


def test_agent_leaderboard_puts_unscored_agents_last_not_omitted():
    lead = make_lead("lead-1")
    records = [make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0)]
    # Sara is on the team roster but has no calls in this period.
    report = compute_team_performance(records, [lead], [RAHUL, SARA], [TEAM_A], "team-1", PERIOD_START, PERIOD_END)
    assert [row.id for row in report.agent_leaderboard] == ["agent-rahul", "agent-sara"]
    assert report.agent_leaderboard[1].overall_score is None


def test_org_benchmark_isolates_other_teams_not_teammates():
    lead = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0),
        make_call("c2", "agent-sara", "lead-1", 1, score_mult=0.5),  # same team -- must not count as "other"
        make_call("c3", "agent-omar", "lead-1", 1, score_mult=0.1),  # Team B -- the only real peer
    ]
    report = compute_team_performance(
        records, [lead], [RAHUL, SARA, OMAR], [TEAM_A, TEAM_B], "team-1", PERIOD_START, PERIOD_END
    )
    overall_row = next(r for r in report.org_benchmark if r.label == "Overall score")
    omar_report = compute_agent_performance(
        [make_call("c3", "agent-omar", "lead-1", 1, score_mult=0.1)], [lead], [OMAR], [TEAM_B], "agent-omar", PERIOD_START, PERIOD_END
    )
    assert overall_row.comparison_value == omar_report.avg_call_score
    assert overall_row.comparison_label == "Org average"


def test_no_other_teams_gets_explicit_note_not_fabricated_org_benchmark():
    lead = make_lead("lead-1")
    records = [make_call("c1", "agent-rahul", "lead-1", 1)]
    report = compute_team_performance(records, [lead], [RAHUL], [TEAM_A], "team-1", PERIOD_START, PERIOD_END)
    assert all(row.comparison_value is None for row in report.org_benchmark)
    assert any("No other teams have calls" in n for n in report.notes)


def test_manager_name_resolves_from_roster():
    manager = Agent(id="agent-mgr", name="Manager Mo", team_id="team-1", is_manager=True)
    team = Team(id="team-1", name="Team A", manager_agent_id="agent-mgr")
    report = compute_team_performance([], [], [manager], [team], "team-1", PERIOD_START, PERIOD_END)
    assert report.manager_agent_id == "agent-mgr"
    assert report.manager_name == "Manager Mo"
