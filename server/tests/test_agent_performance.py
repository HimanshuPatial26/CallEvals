from datetime import date, datetime, timezone

from app.agent_performance import compute_agent_performance
from app.schemas import (
    Agent,
    BuyingIntent,
    CallInsights,
    CallRecord,
    Coaching,
    ComplianceCheck,
    ComplianceCheckResult,
    ComplianceReport,
    DimensionScore,
    ExtractionResult,
    FunnelStage,
    IntentLevel,
    Lead,
    LeadStageEvent,
    NextStep,
    Objection,
    ObjectionCategory,
    ScoreBreakdown,
    Sentiment,
    SentimentLabel,
    Speaker,
    Team,
)

PERIOD_START = date(2026, 8, 1)
PERIOD_END = date(2026, 8, 31)


def _dim(score, max_score=10.0, evidence="ev"):
    return DimensionScore(score=score, max_score=max_score, evidence=evidence)


def _score_breakdown(mult=1.0):
    # mult=1.0 means every dimension scores its own max (100%).
    return ScoreBreakdown(
        opening_rapport=_dim(10 * mult, 10),
        discovery_qualification=_dim(20 * mult, 20),
        active_listening=_dim(10 * mult, 10),
        pitch_value_prop=_dim(15 * mult, 15),
        objection_handling=_dim(15 * mult, 15),
        communication_professionalism=_dim(10 * mult, 10),
        closing_next_steps=_dim(15 * mult, 15),
    )


def make_call(
    call_id: str,
    agent_id: str,
    lead_id: str,
    day: int,
    *,
    with_next_step: bool = True,
    objection_addressed: bool = True,
    sentiment_overall=SentimentLabel.POSITIVE,
    sentiment_beginning=SentimentLabel.NEUTRAL,
    sentiment_end=SentimentLabel.POSITIVE,
    intent=IntentLevel.HIGH,
    score_mult=1.0,
    status="done",
    scored=True,
) -> CallRecord:
    sb = _score_breakdown(score_mult) if scored else None
    extraction = ExtractionResult(
        summary="s",
        next_steps=[NextStep(description="follow up", owner=Speaker.REP, due="tomorrow", confidence=0.9)]
        if with_next_step
        else [],
        objections=[
            Objection(category=ObjectionCategory.PRICE, quote="too expensive", confidence=0.9, addressed=objection_addressed)
        ],
        sentiment=Sentiment(
            overall=sentiment_overall,
            beginning=sentiment_beginning,
            middle=sentiment_overall,
            end=sentiment_end,
            signals=["a signal"],
            confidence=0.8,
        ),
        buying_intent=BuyingIntent(level=intent, signals=["asked about price"], follow_up_priority="soon", confidence=0.8),
        coaching=Coaching(
            top_strength="listens well",
            top_weakness="rushes close",
            behavior_to_stop="x",
            behavior_to_continue="y",
            behavior_to_start="z",
        ),
        score_breakdown=sb,
    )
    compliance = ComplianceReport(
        checks=[ComplianceCheck(rule="Required introduction", result=ComplianceCheckResult.PASS)], adherence_pct=100.0
    )
    overall_score = None
    if scored:
        dims = ["opening_rapport", "discovery_qualification", "active_listening", "pitch_value_prop", "objection_handling", "communication_professionalism", "closing_next_steps"]
        overall_score = sum(getattr(sb, d).score for d in dims) + compliance.adherence_pct / 100 * 5
    insights = CallInsights(
        rep_talk_time_ratio=0.6, longest_rep_monologue_seconds=20, rep_questions_asked=3, customer_questions_asked=1, interruption_count=1
    )
    return CallRecord(
        id=call_id,
        filename="f.wav",
        dual_channel=True,
        created_at=datetime(2026, 8, day, 10, 0, tzinfo=timezone.utc),
        agent_id=agent_id,
        lead_id=lead_id,
        transcript=[],
        extraction=extraction,
        insights=insights,
        compliance=compliance,
        overall_score=overall_score,
        status=status,
    )


def make_lead(lead_id: str, stage=FunnelStage.UNTAGGED, deal_size=None, stage_events=None) -> Lead:
    return Lead(
        id=lead_id,
        display_name=f"Lead {lead_id}",
        stage=stage,
        deal_size_aed=deal_size,
        stage_history=stage_events or [],
        created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )


def stage_event(stage, day, month=8) -> LeadStageEvent:
    return LeadStageEvent(stage=stage, changed_at=datetime(2026, month, day, tzinfo=timezone.utc), changed_by="agent-rahul")


RAHUL = Agent(id="agent-rahul", name="Rahul Sharma", team_id="team-1")
SARA = Agent(id="agent-sara", name="Sara Ali", team_id="team-1")
OMAR = Agent(id="agent-omar", name="Omar Khan", team_id="team-2")  # different team -- not a teammate of Rahul
TEAM_A = Team(id="team-1", name="Team A")
TEAM_B = Team(id="team-2", name="Team B")


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
