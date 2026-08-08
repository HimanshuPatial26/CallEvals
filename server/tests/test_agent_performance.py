from datetime import date, datetime, timezone

from app.agent_performance import compute_agent_performance
from app.schemas import (
    BuyingIntent,
    CallInsights,
    CallOutcome,
    CallRecord,
    Coaching,
    ComplianceCheck,
    ComplianceCheckResult,
    ComplianceReport,
    DimensionScore,
    ExtractionResult,
    FunnelStage,
    IntentLevel,
    NextStep,
    Objection,
    ObjectionCategory,
    ScoreBreakdown,
    Sentiment,
    SentimentLabel,
    Speaker,
)


def _dim(score, max_score=10.0, evidence="ev"):
    return DimensionScore(score=score, max_score=max_score, evidence=evidence)


def _score_breakdown(mult=1.0):
    # mult=1.0 means every dimension scores its own max (100%) — makes the
    # "does the weighted remap sum to 100" test meaningful without needing
    # each dimension's absolute max memorized.
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
    agent: str,
    day: int,
    *,
    with_next_step: bool = True,
    objection_addressed: bool = True,
    sentiment_overall=SentimentLabel.POSITIVE,
    sentiment_beginning=SentimentLabel.NEUTRAL,
    sentiment_end=SentimentLabel.POSITIVE,
    intent=IntentLevel.HIGH,
    stage=FunnelStage.UNTAGGED,
    deal_size=None,
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
        agent_name=agent,
        transcript=[],
        extraction=extraction,
        insights=insights,
        compliance=compliance,
        overall_score=overall_score,
        outcome=CallOutcome(stage=stage, deal_size_aed=deal_size),
        status=status,
    )


PERIOD_START = date(2026, 8, 1)
PERIOD_END = date(2026, 8, 31)


def test_empty_agent_returns_graceful_nones_not_errors():
    report = compute_agent_performance([], "Nobody", PERIOD_START, PERIOD_END)
    assert report.calls_analyzed == 0
    assert report.avg_call_score is None
    assert report.score_breakdown is None
    assert report.consistency_score is None
    assert "No calls have a manually-tagged outcome yet" in " ".join(report.notes)


def test_only_done_calls_count():
    records = [make_call("c1", "Rahul", 1), make_call("c2", "Rahul", 2, status="processing")]
    report = compute_agent_performance(records, "Rahul", PERIOD_START, PERIOD_END)
    assert report.calls_analyzed == 1


def test_agent_filter_excludes_other_agents():
    records = [make_call("c1", "Rahul", 1), make_call("c2", "Sara", 1)]
    report = compute_agent_performance(records, "Rahul", PERIOD_START, PERIOD_END)
    assert report.calls_analyzed == 1


def test_period_filter_excludes_out_of_range_calls():
    records = [make_call("c1", "Rahul", 1), make_call("c2", "Rahul", 5)]
    report = compute_agent_performance(records, "Rahul", date(2026, 8, 3), date(2026, 8, 31))
    assert report.calls_analyzed == 1


def test_score_breakdown_weights_renormalize_to_100():
    records = [make_call("c1", "Rahul", 1)]
    report = compute_agent_performance(records, "Rahul", PERIOD_START, PERIOD_END)
    breakdown = report.score_breakdown
    assert breakdown is not None
    # every dim scored 100/100 except the ones derived from a mixed rescale;
    # with score_mult=1.0 every underlying dim is at its max, so every
    # remapped dim should read 100 and the weighted sum should be 100
    assert breakdown.overall_score == 100.0


def test_score_breakdown_scales_down_with_lower_calls():
    # score_mult only scales the 5 rubric-derived dims (discovery/objection/
    # pitch/closing/communication) — sentiment and compliance are fixed at
    # 100 by make_call's defaults, so the weighted overall lands above 50,
    # not at exactly 50. The point of this test is "lower input -> lower
    # output," not a specific number.
    full = compute_agent_performance([make_call("c1", "Rahul", 1, score_mult=1.0)], "Rahul", PERIOD_START, PERIOD_END)
    half = compute_agent_performance([make_call("c2", "Rahul", 1, score_mult=0.5)], "Rahul", PERIOD_START, PERIOD_END)
    assert half.score_breakdown.overall_score < full.score_breakdown.overall_score
    assert half.score_breakdown.overall_score == 60.5


def test_objection_aggregation_counts_and_addressed_rate():
    records = [
        make_call("c1", "Rahul", 1, objection_addressed=True),
        make_call("c2", "Rahul", 2, objection_addressed=False),
    ]
    report = compute_agent_performance(records, "Rahul", PERIOD_START, PERIOD_END)
    assert report.objections.total_objections == 2
    assert report.objections.overall_handling_effectiveness_pct == 50.0
    assert report.objections.by_category[0].category == ObjectionCategory.PRICE


def test_closing_funnel_leakage_signal():
    records = [
        make_call("c1", "Rahul", 1, with_next_step=True, stage=FunnelStage.QUALIFIED),
        make_call("c2", "Rahul", 2, with_next_step=False, stage=FunnelStage.QUALIFIED),
    ]
    report = compute_agent_performance(records, "Rahul", PERIOD_START, PERIOD_END)
    assert report.closing.qualified_calls == 2
    assert report.closing.qualified_without_next_step == 1
    assert any("fails to log a next step" in c.problem for c in report.coaching_recommendations)


def test_conversion_uses_manually_tagged_outcomes_only():
    records = [
        make_call("c1", "Rahul", 1, stage=FunnelStage.WON, deal_size=500000.0),
        make_call("c2", "Rahul", 2, stage=FunnelStage.LOST),
        make_call("c3", "Rahul", 3, stage=FunnelStage.UNTAGGED),
    ]
    report = compute_agent_performance(records, "Rahul", PERIOD_START, PERIOD_END)
    assert report.conversion.tagged_calls == 2
    assert report.conversion.conversion_rate_pct == round(1 / 3 * 100.0, 1)
    assert report.conversion.revenue_aed == 500000.0
    assert report.conversion.avg_deal_size_aed == 500000.0


def test_sentiment_improvement_and_deterioration_counts():
    records = [
        make_call("c1", "Rahul", 1, sentiment_beginning=SentimentLabel.NEUTRAL, sentiment_end=SentimentLabel.POSITIVE),
        make_call("c2", "Rahul", 2, sentiment_beginning=SentimentLabel.POSITIVE, sentiment_end=SentimentLabel.NEGATIVE),
    ]
    report = compute_agent_performance(records, "Rahul", PERIOD_START, PERIOD_END)
    assert report.sentiment.calls_improved == 1
    assert report.sentiment.calls_deteriorated == 1


def test_consistency_score_is_lower_with_more_score_variance():
    stable = [make_call("c1", "Rahul", 1, score_mult=1.0), make_call("c2", "Rahul", 2, score_mult=1.0)]
    volatile = [make_call("c3", "Sara", 1, score_mult=1.0), make_call("c4", "Sara", 2, score_mult=0.3)]
    stable_report = compute_agent_performance(stable, "Rahul", PERIOD_START, PERIOD_END)
    volatile_report = compute_agent_performance(volatile, "Sara", PERIOD_START, PERIOD_END)
    assert stable_report.consistency_score == 100.0
    assert volatile_report.consistency_score < stable_report.consistency_score


def test_team_benchmark_uses_other_agents_only():
    records = [
        make_call("c1", "Rahul", 1, score_mult=1.0),
        make_call("c2", "Sara", 1, score_mult=0.5),
    ]
    report = compute_agent_performance(records, "Rahul", PERIOD_START, PERIOD_END)
    overall_row = next(r for r in report.team_benchmark if r.label == "Overall score")
    assert overall_row.agent_value == report.avg_call_score
    assert overall_row.comparison_value != report.avg_call_score  # comes from Sara, not Rahul


def test_no_team_data_notes_it_rather_than_fabricating():
    records = [make_call("c1", "Rahul", 1)]
    report = compute_agent_performance(records, "Rahul", PERIOD_START, PERIOD_END)
    assert all(row.comparison_value is None for row in report.team_benchmark if row.label == "Overall score")
    assert any("No other agents" in n for n in report.notes)


def test_performance_trend_compares_to_prior_equal_length_period():
    current_period_start = date(2026, 8, 1)
    current_period_end = date(2026, 8, 5)
    current_calls = [make_call("c1", "Rahul", 2, score_mult=1.0)]
    prev_call = make_call("c0", "Rahul", 30, score_mult=0.5)
    prev_call.created_at = prev_call.created_at.replace(month=7, day=28)  # inside the 5-day window before Aug 1
    report = compute_agent_performance(current_calls + [prev_call], "Rahul", current_period_start, current_period_end)
    assert report.performance_trend_pct is not None
    assert report.performance_trend_pct > 0  # improved vs. the lower-scored prior period
