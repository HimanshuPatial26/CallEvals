from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class Speaker(str, Enum):
    REP = "rep"
    CUSTOMER = "customer"
    UNKNOWN = "unknown"


class ObjectionCategory(str, Enum):
    """F4. Originally three categories (see PRD section 5); expanded to the
    full taxonomy from the analytics requirements doc section 10 by explicit
    product decision — narrower scope kept precision high at launch, but
    coverage now matters more than the original three-category discipline."""

    PRICE = "price"
    TIMING = "timing"
    COMPETITOR = "competitor"
    NEED = "need"
    TRUST = "trust"
    AUTHORITY = "authority"
    PRODUCT = "product"
    IMPLEMENTATION = "implementation"
    CONTRACT = "contract"
    SWITCHING_COST = "switching_cost"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class IntentLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceCheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    NOT_APPLICABLE = "not_applicable"


class FunnelStage(str, Enum):
    """Manually set by the manager reviewing the call — not extracted or
    inferred. The app has no CRM/dialer integration (PRD section 8: CRM
    moves to Phase 2 as a hard dependency), so conversion/funnel/revenue
    analytics have no data source unless a human records the outcome. This
    is that record, kept deliberately minimal rather than modeling a full
    CRM pipeline."""

    UNTAGGED = "untagged"
    QUALIFIED = "qualified"
    DEMO_BOOKED = "demo_booked"
    PROPOSAL_SENT = "proposal_sent"
    WON = "won"
    LOST = "lost"


class TranscriptSegment(BaseModel):
    """One speaker turn. F1 output."""

    speaker: Speaker
    start: float = Field(description="Seconds from call start")
    end: float
    text: str


class NextStep(BaseModel):
    """F3 output — the easiest output for a manager to verify, so it's the trust anchor."""

    description: str
    owner: Speaker
    due: str | None = Field(default=None, description="Free-text due date/time as stated on the call, if any")
    source_timestamp: float | None = Field(
        default=None, description="Start time of the transcript segment this was extracted from"
    )
    confidence: float = Field(ge=0.0, le=1.0)


class Objection(BaseModel):
    """F4 output."""

    category: ObjectionCategory
    quote: str = Field(description="The customer's own words, not a paraphrase")
    source_timestamp: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    addressed: bool = Field(
        description="Whether the rep responded to this objection later in the call, per the model's read of the transcript"
    )


class Sentiment(BaseModel):
    """Analytics doc section 11. PRD section 5 originally cut sentiment as
    low-precision and the least actionable output in this category — kept as
    an explicit, low-confidence-labeled signal by product decision rather
    than a claim of measured emotion."""

    overall: SentimentLabel
    beginning: SentimentLabel
    middle: SentimentLabel
    end: SentimentLabel
    signals: list[str] = Field(
        default_factory=list, description="Short phrases naming what drove the read, e.g. 'hesitation on price', 'enthusiasm about timeline'"
    )
    confidence: float = Field(ge=0.0, le=1.0)


class BuyingIntent(BaseModel):
    """Analytics doc section 12. Deliberately separate from Sentiment — a
    positive customer is not necessarily ready to buy."""

    level: IntentLevel
    signals: list[str] = Field(default_factory=list, description="Quotes or paraphrased moments that drove the level")
    follow_up_priority: str = Field(description="Free-text recommended urgency/timing for follow-up")
    confidence: float = Field(ge=0.0, le=1.0)


class Coaching(BaseModel):
    """Analytics doc section 20, reduced to the fields a manager can act on
    without a training-content library backing 'recommended module'."""

    top_strength: str
    top_weakness: str
    behavior_to_stop: str
    behavior_to_continue: str
    behavior_to_start: str


class DimensionScore(BaseModel):
    """One weighted dimension of the analytics doc's section 18 scorecard.
    `max_score` carries the dimension's weight so the UI never hardcodes it
    twice, and every score ships with the evidence line section 19 requires —
    no dimension score without a transcript-grounded reason."""

    score: float
    max_score: float
    evidence: str = Field(description="Transcript-grounded reason for this score, per doc section 19")


class ScoreBreakdown(BaseModel):
    """The seven LLM-scored dimensions of the doc's section 18 rubric.
    Compliance (the eighth, worth 5 of 100) is deliberately not here — it's
    computed deterministically in app/compliance.py, not judged by the model,
    and combined with these into CallRecord.overall_score by the pipeline."""

    opening_rapport: DimensionScore
    discovery_qualification: DimensionScore
    active_listening: DimensionScore
    pitch_value_prop: DimensionScore
    objection_handling: DimensionScore
    communication_professionalism: DimensionScore
    closing_next_steps: DimensionScore


class ComplianceCheck(BaseModel):
    rule: str
    result: ComplianceCheckResult
    evidence: str | None = None


class ComplianceReport(BaseModel):
    """Rule-based, not LLM — analytics doc section 14 asks for configurable
    pass/fail checks against the org's own process, which is a keyword/pattern
    match problem, not a semantic-judgment one. Zero added inference cost,
    same reasoning as CallInsights."""

    checks: list[ComplianceCheck] = Field(default_factory=list)
    adherence_pct: float = Field(ge=0.0, le=100.0, description="Share of applicable checks that passed")


class ExtractionResult(BaseModel):
    """F2 + F3 + F4 combined, plus the analytics-doc expansion (sentiment,
    buying intent, coaching, rubric scores) — the LLM extraction step's
    output shape. The new fields are optional so existing callers/fakes that
    only set summary/next_steps/objections still validate."""

    summary: str = Field(description="Under 150 words per PRD F2")
    next_steps: list[NextStep] = Field(default_factory=list)
    objections: list[Objection] = Field(default_factory=list)
    sentiment: Sentiment | None = None
    buying_intent: BuyingIntent | None = None
    coaching: Coaching | None = None
    score_breakdown: ScoreBreakdown | None = None


class CallInsights(BaseModel):
    """Objective, transcript-derived behavior signals — pure computation over
    segment timestamps and text, no LLM call, no added cost, no score.

    Deliberately NOT a composite number: PRD section 5 rejected single-score
    call scoring for getting gamed and reading as surveillance to reps. These
    are individual, factual readouts a manager looks at and decides what (if
    anything) to coach on — same "flags, not scores" philosophy the PRD
    already applies to next-step and objection extraction.

    Only computed when the transcript actually distinguishes rep from
    customer (dual-channel, or a diarized call) — a mono call with every
    segment labeled Speaker.UNKNOWN has nothing to compute this from.
    """

    rep_talk_time_ratio: float = Field(
        ge=0.0, le=1.0, description="Share of total speaking time (rep + customer) that was the rep"
    )
    longest_rep_monologue_seconds: float = Field(
        description="Longest uninterrupted stretch of consecutive rep turns"
    )
    rep_questions_asked: int = Field(
        description="Rep segments containing '?' — a heuristic count, not a verified discovery-question intent"
    )
    customer_questions_asked: int = Field(description="Same heuristic, applied to customer segments")
    interruption_count: int = Field(
        description="Adjacent segments where the next speaker started before the previous one finished, either direction"
    )


class CallOutcome(BaseModel):
    """The manually-tagged funnel stage + deal size behind every CRM-shaped
    agent-performance metric (conversion rate, qualified-lead rate, revenue,
    the quality-vs-outcome matrix). Defaults to untagged/unknown — an
    unreviewed call should never silently count as "lost" or "$0"."""

    stage: FunnelStage = FunnelStage.UNTAGGED
    deal_size_aed: float | None = Field(default=None, ge=0.0, description="Only meaningful once stage=won")


class ReviewFeedback(BaseModel):
    """Manager confirm/reject on an extracted next step or objection.

    This is the raw signal behind the A1 extraction-precision metric (PRD section 6) —
    every confirm/reject a manager clicks is one labeled data point.
    """

    item_type: str = Field(description="'next_step' or 'objection'")
    item_index: int
    confirmed: bool


class CallRecord(BaseModel):
    id: str
    filename: str
    dual_channel: bool
    created_at: datetime
    agent_name: str = Field(
        default="Unassigned", description="Rep who handled this call, captured at upload time — required for any agent-level rollup"
    )
    transcript: list[TranscriptSegment] = Field(default_factory=list)
    extraction: ExtractionResult | None = None
    insights: CallInsights | None = None
    compliance: ComplianceReport | None = None
    overall_score: float | None = Field(
        default=None,
        description="Sum of the 7 LLM-scored rubric dimensions plus the compliance-derived score, out of 100 (doc section 18)",
    )
    outcome: CallOutcome = Field(default_factory=CallOutcome)
    feedback: list[ReviewFeedback] = Field(default_factory=list)
    status: str = Field(default="processing", description="processing | done | failed")
    error: str | None = None


# --- Agent performance aggregation (cross-call rollups, app/agent_performance.py) ---
#
# Everything below is computed by summing/averaging fields already produced
# per-call above — no new LLM call, no new extraction. Two things the source
# doc asked for are deliberately NOT modeled here (see AgentPerformanceReport.notes):
# dialer-level call volume (assigned/attempted/connected/missed — this app only
# ever sees a call once someone uploads a recording, so "attempted but not
# connected" has no data source), and itemized discovery-field percentages
# (need/budget/timeline/decision-maker identified individually — the per-call
# extraction only produces one aggregate discovery score + evidence string,
# and adding seven new boolean fields there is out of scope for this pass).


class ScoreDimensionAgg(BaseModel):
    label: str
    agent_score: float = Field(description="0-100, rescaled from the dimension's own per-call max")
    team_benchmark: float | None = Field(
        default=None, description="0-100 average across other agents' calls in the same period; None without team data yet"
    )
    calls_scored: int


class AgentScoreBreakdown(BaseModel):
    """Doc section 2's 8-dimension rubric, remapped onto the ScoreBreakdown
    already computed per call rather than re-extracting a different one (see
    the PRD addendum for the reasoning). Call Discipline has no defined
    scoring method in either source doc, so it's excluded and the remaining
    7 weights are renormalized to still sum to 100 rather than silently
    capping the total at 95."""

    discovery_qualification: ScoreDimensionAgg
    objection_handling: ScoreDimensionAgg
    pitch_value_prop: ScoreDimensionAgg
    closing_next_steps: ScoreDimensionAgg
    communication: ScoreDimensionAgg = Field(
        description="Remapped from the average of opening_rapport, active_listening, and communication_professionalism"
    )
    sentiment: ScoreDimensionAgg = Field(description="Sentiment label converted to a 0-100 score: positive=100, neutral=60, negative=20")
    compliance: ScoreDimensionAgg
    overall_score: float = Field(description="Weighted sum of the 7 dimensions above, renormalized to 100")
    call_discipline_excluded_note: str = "Not scored — no defined measurement method in either source doc."


class TalkTimeAgg(BaseModel):
    avg_rep_talk_pct: float
    avg_customer_talk_pct: float
    avg_interruptions: float
    avg_questions_per_call: float
    avg_longest_monologue_seconds: float
    team_avg_rep_talk_pct: float | None = None


class ObjectionCategoryAgg(BaseModel):
    category: ObjectionCategory
    count: int
    frequency_pct: float
    addressed_rate_pct: float = Field(description="Share of this category's objections marked addressed:true — a handling-score proxy")


class ObjectionAgg(BaseModel):
    total_objections: int
    by_category: list[ObjectionCategoryAgg]
    overall_handling_effectiveness_pct: float | None
    weakest_category: ObjectionCategory | None = None


class ClosingAgg(BaseModel):
    calls_with_next_step: int = Field(description="Heuristic proxy for 'closing attempt' — no separate manual signal for it")
    calls_with_due_date: int
    qualified_calls: int
    demo_booked: int
    proposals_sent: int
    won: int
    lost: int
    qualified_without_next_step: int = Field(
        description="Qualified calls that ended with no logged next step — the funnel-leakage signal doc section 11 calls out"
    )


class SentimentAgg(BaseModel):
    avg_beginning_score: float
    avg_end_score: float
    sentiment_improvement: float = Field(description="avg_end_score - avg_beginning_score")
    calls_improved: int
    calls_deteriorated: int
    positive_pct: float
    negative_pct: float


class IntentDistribution(BaseModel):
    level: IntentLevel
    count: int
    pct: float
    conversion_rate_pct: float | None = None


class ConversionAgg(BaseModel):
    """Entirely dependent on manually-tagged CallOutcome. None fields mean
    'not enough tagged calls to compute this', never a silent zero."""

    tagged_calls: int
    qualified_rate_pct: float | None
    conversion_rate_pct: float | None
    lost_rate_pct: float | None
    revenue_aed: float | None
    avg_deal_size_aed: float | None
    intent_breakdown: list[IntentDistribution]


class QualityBucket(BaseModel):
    range_label: str
    count: int
    pct: float


class TrendPoint(BaseModel):
    period_label: str
    calls: int
    avg_score: float | None
    conversion_rate_pct: float | None


class StrengthWeakness(BaseModel):
    dimension: str
    score: float
    note: str


class CoachingRecommendation(BaseModel):
    problem: str
    evidence: str
    recommendation: str


class BenchmarkRow(BaseModel):
    label: str
    agent_value: float
    comparison_value: float | None
    comparison_label: str


class QualityOutcomeQuadrant(BaseModel):
    quadrant: str = Field(description="star_performer | investigate_leads | strong_but_risky | needs_coaching")
    quality_score: float
    outcome_conversion_pct: float | None


class AgentPerformanceReport(BaseModel):
    """The full cross-call rollup for one agent over one period — everything
    computed from data the app already has, plus manually-tagged outcomes.
    See the module docstring above for what's deliberately not modeled."""

    agent_name: str
    period_start: date
    period_end: date

    calls_analyzed: int
    calls_scored: int = Field(description="Calls with an overall_score — i.e. extraction succeeded with a score_breakdown")

    avg_call_score: float | None
    avg_customer_sentiment_score: float | None
    compliance_score_pct: float | None
    performance_trend_pct: float | None = Field(
        default=None,
        description="Change in avg_call_score vs. the immediately preceding period of equal length; None without a full prior period",
    )

    score_breakdown: AgentScoreBreakdown | None

    talk_time: TalkTimeAgg | None
    discovery_avg_score: float | None
    objections: ObjectionAgg
    closing: ClosingAgg
    sentiment: SentimentAgg | None
    conversion: ConversionAgg

    quality_distribution: list[QualityBucket]
    consistency_score: float | None = Field(description="100 minus the normalized stdev of per-call overall_score; higher = more stable")

    trend: list[TrendPoint]
    strengths: list[StrengthWeakness]
    weaknesses: list[StrengthWeakness]
    coaching_recommendations: list[CoachingRecommendation]

    team_benchmark: list[BenchmarkRow]
    quality_outcome_matrix: QualityOutcomeQuadrant | None

    notes: list[str] = Field(
        default_factory=list, description="Explicit call-outs for what the source doc asked for that isn't computed here, and why"
    )
