"""Shared test data builders for the agent/team/org performance test suites.
Not a test_*.py file on purpose — pytest shouldn't try to collect tests from
it, it's just factories the three performance-rollup test files all need.
"""

from datetime import date, datetime, timezone

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
    LostReason,
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


def make_lead(
    lead_id: str,
    stage=FunnelStage.UNTAGGED,
    deal_size=None,
    stage_events=None,
    source: str | None = None,
    lost_reason: LostReason | None = None,
    created_day: int = 1,
) -> Lead:
    return Lead(
        id=lead_id,
        display_name=f"Lead {lead_id}",
        source=source,
        stage=stage,
        deal_size_aed=deal_size,
        lost_reason=lost_reason,
        stage_history=stage_events or [],
        created_at=datetime(2026, 7, created_day, tzinfo=timezone.utc),
    )


def stage_event(stage, day, month=8) -> LeadStageEvent:
    return LeadStageEvent(stage=stage, changed_at=datetime(2026, month, day, tzinfo=timezone.utc), changed_by="agent-rahul")


RAHUL = Agent(id="agent-rahul", name="Rahul Sharma", team_id="team-1")
SARA = Agent(id="agent-sara", name="Sara Ali", team_id="team-1")
OMAR = Agent(id="agent-omar", name="Omar Khan", team_id="team-2")  # different team -- not a teammate of Rahul
TEAM_A = Team(id="team-1", name="Team A")
TEAM_B = Team(id="team-2", name="Team B")
