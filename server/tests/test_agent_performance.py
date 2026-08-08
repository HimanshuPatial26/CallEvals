from datetime import date, datetime, timezone

from app.agent_performance import compute_agent_performance
from app.schemas import Agent, FunnelStage, IntentLevel, LeadStageEvent, ObjectionCategory, SentimentLabel
from tests.factories import OMAR, PERIOD_END, PERIOD_START, RAHUL, SARA, TEAM_A, TEAM_B, make_call, make_lead, stage_event


def test_empty_agent_returns_graceful_nones_not_errors():
    report = compute_agent_performance([], [], [RAHUL], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END)
    assert report.agent_id == "agent-rahul"
    assert report.agent_name == "Rahul Sharma"
    assert report.calls_analyzed == 0
    assert report.avg_call_score is None
    assert report.score_breakdown is None
    assert report.consistency_score is None


def test_agent_not_in_roster_falls_back_to_id_as_name():
    report = compute_agent_performance([], [], [], [], "ghost-agent", PERIOD_START, PERIOD_END)
    assert report.agent_name == "ghost-agent"
    assert report.team_id is None


def test_only_done_calls_count():
    lead = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1),
        make_call("c2", "agent-rahul", "lead-1", 2, status="processing"),
    ]
    report = compute_agent_performance(records, [lead], [RAHUL], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END)
    assert report.calls_analyzed == 1


def test_agent_filter_excludes_other_agents():
    lead = make_lead("lead-1")
    records = [make_call("c1", "agent-rahul", "lead-1", 1), make_call("c2", "agent-sara", "lead-1", 1)]
    report = compute_agent_performance(records, [lead], [RAHUL, SARA], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END)
    assert report.calls_analyzed == 1


def test_period_filter_excludes_out_of_range_calls():
    lead = make_lead("lead-1")
    records = [make_call("c1", "agent-rahul", "lead-1", 1), make_call("c2", "agent-rahul", "lead-1", 5)]
    report = compute_agent_performance(records, [lead], [RAHUL], [TEAM_A], "agent-rahul", date(2026, 8, 3), PERIOD_END)
    assert report.calls_analyzed == 1


def test_score_breakdown_weights_renormalize_to_100():
    lead = make_lead("lead-1")
    records = [make_call("c1", "agent-rahul", "lead-1", 1)]
    report = compute_agent_performance(records, [lead], [RAHUL], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END)
    assert report.score_breakdown.overall_score == 100.0


def test_score_breakdown_scales_down_with_lower_calls():
    lead = make_lead("lead-1")
    full = compute_agent_performance(
        [make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0)], [lead], [RAHUL], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END
    )
    half = compute_agent_performance(
        [make_call("c2", "agent-rahul", "lead-1", 1, score_mult=0.5)], [lead], [RAHUL], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END
    )
    assert half.score_breakdown.overall_score < full.score_breakdown.overall_score
    assert half.score_breakdown.overall_score == 60.5


def test_objection_aggregation_counts_and_addressed_rate():
    lead = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1, objection_addressed=True),
        make_call("c2", "agent-rahul", "lead-1", 2, objection_addressed=False),
    ]
    report = compute_agent_performance(records, [lead], [RAHUL], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END)
    assert report.objections.total_objections == 2
    assert report.objections.overall_handling_effectiveness_pct == 50.0
    assert report.objections.by_category[0].category == ObjectionCategory.PRICE


def test_closing_funnel_leakage_is_lead_level_not_call_level():
    # lead-1: qualified, its only call has a next step -> not leaking
    # lead-2: qualified, its only call has no next step -> leaking
    lead1 = make_lead("lead-1", stage=FunnelStage.QUALIFIED)
    lead2 = make_lead("lead-2", stage=FunnelStage.QUALIFIED)
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1, with_next_step=True),
        make_call("c2", "agent-rahul", "lead-2", 2, with_next_step=False),
    ]
    report = compute_agent_performance(records, [lead1, lead2], [RAHUL], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END)
    assert report.closing.qualified_leads == 2
    assert report.closing.qualified_leads_without_next_step == 1
    assert any("fails to log a next step" in c.problem for c in report.coaching_recommendations)


def test_conversion_counts_leads_not_calls():
    # lead-1 called twice by the same agent -> still ONE lead in the denominator
    lead1 = make_lead("lead-1", stage=FunnelStage.WON, deal_size=500000.0, stage_events=[stage_event(FunnelStage.WON, 15)])
    lead2 = make_lead("lead-2", stage=FunnelStage.LOST, stage_events=[stage_event(FunnelStage.LOST, 10)])
    lead3 = make_lead("lead-3")  # untagged
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1),
        make_call("c2", "agent-rahul", "lead-1", 2),  # same lead again
        make_call("c3", "agent-rahul", "lead-2", 3),
        make_call("c4", "agent-rahul", "lead-3", 4),
    ]
    report = compute_agent_performance(records, [lead1, lead2, lead3], [RAHUL], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END)
    assert report.conversion.leads_touched == 3
    assert report.conversion.leads_tagged == 2
    assert report.conversion.conversion_rate_pct == round(1 / 3 * 100.0, 1)
    assert report.conversion.lost_rate_pct == 50.0
    assert report.conversion.revenue_aed == 500000.0


def test_conversion_only_counts_wins_that_happened_within_the_period():
    # lead won back in June -- currently sitting at "won" -- but querying
    # August shouldn't count it as an August conversion.
    lead = make_lead(
        "lead-1", stage=FunnelStage.WON, deal_size=500000.0, stage_events=[LeadStageEvent(stage=FunnelStage.WON, changed_at=datetime(2026, 6, 15, tzinfo=timezone.utc))]
    )
    records = [make_call("c1", "agent-rahul", "lead-1", 5)]  # a follow-up call in August
    report = compute_agent_performance(records, [lead], [RAHUL], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END)
    assert report.conversion.conversion_rate_pct == 0.0
    assert report.conversion.revenue_aed is None
    # but the current-stage snapshot in ClosingAgg still reflects reality
    assert report.closing.won_leads == 1


def test_sentiment_improvement_and_deterioration_counts():
    lead = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1, sentiment_beginning=SentimentLabel.NEUTRAL, sentiment_end=SentimentLabel.POSITIVE),
        make_call("c2", "agent-rahul", "lead-1", 2, sentiment_beginning=SentimentLabel.POSITIVE, sentiment_end=SentimentLabel.NEGATIVE),
    ]
    report = compute_agent_performance(records, [lead], [RAHUL], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END)
    assert report.sentiment.calls_improved == 1
    assert report.sentiment.calls_deteriorated == 1


def test_consistency_score_is_lower_with_more_score_variance():
    lead = make_lead("lead-1")
    stable = [make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0), make_call("c2", "agent-rahul", "lead-1", 2, score_mult=1.0)]
    volatile = [make_call("c3", "agent-sara", "lead-1", 1, score_mult=1.0), make_call("c4", "agent-sara", "lead-1", 2, score_mult=0.3)]
    stable_report = compute_agent_performance(stable, [lead], [RAHUL, SARA], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END)
    volatile_report = compute_agent_performance(volatile, [lead], [RAHUL, SARA], [TEAM_A], "agent-sara", PERIOD_START, PERIOD_END)
    assert stable_report.consistency_score == 100.0
    assert volatile_report.consistency_score < stable_report.consistency_score


def test_team_benchmark_only_includes_real_teammates():
    lead = make_lead("lead-1")
    records = [
        make_call("c1", "agent-rahul", "lead-1", 1, score_mult=1.0),
        make_call("c2", "agent-sara", "lead-1", 1, score_mult=0.5),  # teammate (team-1)
        make_call("c3", "agent-omar", "lead-1", 1, score_mult=0.1),  # NOT a teammate (team-2)
    ]
    report = compute_agent_performance(
        records, [lead], [RAHUL, SARA, OMAR], [TEAM_A, TEAM_B], "agent-rahul", PERIOD_START, PERIOD_END
    )
    overall_row = next(r for r in report.team_benchmark if r.label == "Overall score")
    assert overall_row.agent_value == report.avg_call_score
    # comparison must come from Sara only (0.5 mult), never from Omar (0.1 mult)
    sara_only_report = compute_agent_performance(
        [make_call("c2", "agent-sara", "lead-1", 1, score_mult=0.5)], [lead], [RAHUL, SARA, OMAR], [TEAM_A, TEAM_B],
        "agent-sara", PERIOD_START, PERIOD_END,
    )
    assert overall_row.comparison_value == sara_only_report.avg_call_score


def test_agent_with_no_team_gets_explicit_note_not_fabricated_benchmark():
    lone_agent = Agent(id="agent-lone", name="Lone Wolf", team_id=None)
    lead = make_lead("lead-1")
    report = compute_agent_performance(
        [make_call("c1", "agent-lone", "lead-1", 1)], [lead], [lone_agent], [], "agent-lone", PERIOD_START, PERIOD_END
    )
    assert all(row.comparison_value is None for row in report.team_benchmark)
    assert any("no team assigned" in n for n in report.notes)


def test_agent_with_team_but_no_teammate_data_gets_explicit_note():
    lead = make_lead("lead-1")
    report = compute_agent_performance(
        [make_call("c1", "agent-rahul", "lead-1", 1)], [lead], [RAHUL, SARA], [TEAM_A], "agent-rahul", PERIOD_START, PERIOD_END
    )
    assert any("No teammates have calls" in n for n in report.notes)


def test_performance_trend_compares_to_prior_equal_length_period():
    lead = make_lead("lead-1")
    current_period_start = date(2026, 8, 1)
    current_period_end = date(2026, 8, 5)
    current_calls = [make_call("c1", "agent-rahul", "lead-1", 2, score_mult=1.0)]
    prev_call = make_call("c0", "agent-rahul", "lead-1", 30, score_mult=0.5)
    prev_call.created_at = prev_call.created_at.replace(month=7, day=28)  # inside the 5-day window before Aug 1
    report = compute_agent_performance(
        current_calls + [prev_call], [lead], [RAHUL], [TEAM_A], "agent-rahul", current_period_start, current_period_end
    )
    assert report.performance_trend_pct is not None
    assert report.performance_trend_pct > 0  # improved vs. the lower-scored prior period
