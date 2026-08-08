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


class LostReason(str, Enum):
    """ROADMAP.md C3 (doc section 17: "reasons customers reject the
    product"). Deliberately not ObjectionCategory reused — a lost reason
    answers "why this deal ultimately died," a different axis than "what
    concern came up on a call": a lead can raise a price objection and
    still close, or go quiet with no objection ever raised and still be
    lost. Set only when stage=lost; see Lead.lost_reason."""

    PRICE = "price"
    TIMING = "timing"
    COMPETITOR = "competitor"
    FINANCING = "financing"
    UNRESPONSIVE = "unresponsive"
    NOT_QUALIFIED = "not_qualified"
    CHANGED_MIND = "changed_mind"
    OTHER = "other"


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


class ReviewFeedback(BaseModel):
    """Manager confirm/reject on an extracted next step or objection.

    This is the raw signal behind the A1 extraction-precision metric (PRD section 6) —
    every confirm/reject a manager clicks is one labeled data point.
    """

    item_type: str = Field(description="'next_step' or 'objection'")
    item_index: int
    confirmed: bool


# --- Roster & lead identity (ROADMAP.md Phase A) ---
#
# Replaces the free-text agent_name / call-level CallOutcome from the
# previous pass. A real org has a roster (who's on which team) and leads
# that outlive any single call (a lead gets called multiple times before it
# converts) — neither existed before this. No Organization entity yet:
# nothing in this pass needs one, and it stays out until Phase B's org
# rollup actually requires it.


class Team(BaseModel):
    id: str
    name: str
    manager_agent_id: str | None = Field(default=None, description="FK to Agent — a manager is an agent record, not a separate entity")


class Agent(BaseModel):
    id: str
    name: str
    team_id: str | None = Field(default=None, description="None = not yet assigned to a team")
    is_manager: bool = False
    active: bool = True


class LeadStageEvent(BaseModel):
    """One entry in a lead's stage history. Conversion metrics key off
    *when* a lead reached a stage, not just its current stage — a lead that
    won six months ago shouldn't inflate this month's conversion rate just
    because someone views the report today."""

    stage: FunnelStage
    changed_at: datetime
    changed_by: str | None = Field(default=None, description="Agent id or free text; None until auth exists (ROADMAP Phase E)")


class AssignmentEvent(BaseModel):
    """One entry in a lead's reassignment history (ROADMAP.md C6). Only
    written on an explicit reassignment via POST /api/leads/{id}/reassign —
    the initial assignment at lead creation is not itself an event, same
    convention as stage_history only recording explicit stage changes, not
    the initial UNTAGGED default."""

    assigned_agent_id: str | None
    changed_at: datetime
    changed_by: str | None = Field(default=None, description="Agent id or free text; None until auth exists (ROADMAP Phase E)")


class Lead(BaseModel):
    """A prospect, independent of any single call. Replaces the previous
    call-level CallOutcome — a lead's funnel stage is the single source of
    truth for conversion, not whichever call happened to get tagged."""

    id: str
    display_name: str
    phone: str | None = None
    source: str | None = Field(default=None, description="Free text for now — no fixed channel/campaign taxonomy yet")
    assigned_agent_id: str | None = None
    stage: FunnelStage = FunnelStage.UNTAGGED
    deal_size_aed: float | None = Field(default=None, ge=0.0, description="Only meaningful once stage=won")
    lost_reason: LostReason | None = Field(default=None, description="Only meaningful once stage=lost")
    stage_history: list[LeadStageEvent] = Field(default_factory=list)
    assignment_history: list[AssignmentEvent] = Field(default_factory=list)
    created_at: datetime


class LeadCallSummary(BaseModel):
    """A trimmed call reference for Lead detail views — full CallRecord
    (transcript, extraction) is fetched separately via GET /api/calls/{id}
    when actually needed; a lead's call history doesn't need every
    transcript segment just to list "5 calls, most recent Aug 3"."""

    id: str
    created_at: datetime
    agent_id: str
    overall_score: float | None
    status: str


class LeadDetail(Lead):
    calls: list[LeadCallSummary] = Field(default_factory=list)


class CallRecord(BaseModel):
    id: str
    filename: str
    dual_channel: bool
    created_at: datetime
    agent_id: str = Field(description="FK to Agent — required, every call is attributed to a real roster entry")
    lead_id: str = Field(description="FK to Lead — required, every call is attributed to a real lead")
    transcript: list[TranscriptSegment] = Field(default_factory=list)
    extraction: ExtractionResult | None = None
    insights: CallInsights | None = None
    compliance: ComplianceReport | None = None
    overall_score: float | None = Field(
        default=None,
        description="Sum of the 7 LLM-scored rubric dimensions plus the compliance-derived score, out of 100 (doc section 18)",
    )
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
    """Field names say "agent" because that's where this was first built
    (ROADMAP.md Phase A), but the same shape is reused unchanged at team and
    org level (Phase B) — agent_score is "this rollup's score" whoever it's
    for, and team_benchmark is "peer comparison" against whatever the peer
    group is at that level (teammates for an agent, other teams for a team).
    Not renamed generic to avoid rippling a cosmetic change through already-
    tested code and the frontend; the meaning is unambiguous from context."""

    label: str
    agent_score: float = Field(description="0-100, rescaled from the dimension's own per-call max")
    team_benchmark: float | None = Field(
        default=None, description="0-100 average across the relevant peer group in the same period (teammates for an agent, other teams for a team); None without peer data yet"
    )
    calls_scored: int


class AgentScoreBreakdown(BaseModel):
    """Doc section 2's 8-dimension rubric, remapped onto the ScoreBreakdown
    already computed per call rather than re-extracting a different one (see
    the PRD addendum for the reasoning). Call Discipline has no defined
    scoring method in either source doc, so it's excluded and the remaining
    7 weights are renormalized to still sum to 100 rather than silently
    capping the total at 95. Despite the name, this same shape is reused for
    team- and org-level rollups (Phase B) — see ScoreDimensionAgg's note."""

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
    team_avg_rep_talk_pct: float | None = Field(default=None, description="Average across this agent's teammates, not the whole org")


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
    """Current-snapshot counts, not period-scoped events: "of the leads I
    talked to this period, how many are, right now, sitting in each funnel
    column." Distinct from ConversionAgg.conversion_rate_pct, which counts
    only the leads that actually *transitioned* to won during this specific
    period — a lead currently sitting at "won" might have converted last
    quarter, which this section would still count but conversion_rate_pct
    would not."""

    calls_with_next_step: int = Field(description="Heuristic proxy for 'closing attempt' — no separate manual signal for it")
    calls_with_due_date: int
    qualified_leads: int = Field(description="Distinct leads touched this period whose current stage != untagged")
    demo_booked_leads: int
    proposals_sent_leads: int
    won_leads: int = Field(description="Current-stage snapshot, not period-scoped — see class docstring")
    lost_leads: int
    qualified_leads_without_next_step: int = Field(
        description="Qualified leads where none of this agent's calls to them (in period) logged a next step — the funnel-leakage signal doc section 11 calls out"
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
    """Lead-level conversion (ROADMAP.md C1) — entirely dependent on
    manually-tagged Lead.stage / stage_history, since there's no CRM
    integration. None fields mean 'not enough data to compute this', never
    a silent zero.

    conversion_rate_pct and lost_rate_pct are period-scoped: a lead only
    counts if its stage_history shows it *transitioning* to won/lost during
    this specific period, not merely sitting at that stage when queried —
    see ClosingAgg's docstring for why that distinction matters."""

    leads_touched: int = Field(description="Distinct leads with >=1 call from this agent in the period — the denominator for every rate below")
    leads_tagged: int = Field(description="Of leads_touched, how many have ever had their stage set past untagged")
    qualified_rate_pct: float | None
    conversion_rate_pct: float | None = Field(description="Leads that transitioned to won during this period / leads_touched")
    lost_rate_pct: float | None = Field(description="Leads that transitioned to lost during this period / leads_tagged")
    revenue_aed: float | None = Field(description="Sum of deal_size_aed for leads that won during this period")
    avg_deal_size_aed: float | None
    intent_breakdown: list[IntentDistribution]


class CallVolumeBucket(BaseModel):
    range_label: str
    count: int
    pct: float


class CallsToCloseAgg(BaseModel):
    """How many touches (calls) and how many days it takes to close a deal
    (ROADMAP.md C2) — a real sales-ops question the rollup couldn't answer
    at all before this. calls_per_lead_distribution buckets every distinct
    lead touched in the period (not just won ones); avg_calls_to_close and
    avg_days_to_close are computed only over leads that transitioned to won
    *within this period* (same period-scoped rule as
    ConversionAgg.conversion_rate_pct), counting only calls made up to and
    including the day of that transition — a courtesy call placed after the
    deal already closed shouldn't inflate "how many calls did it take"."""

    calls_per_lead_distribution: list[CallVolumeBucket]
    avg_calls_to_close: float | None
    avg_days_to_close: float | None
    won_leads_measured: int = Field(description="How many won-in-period leads the two averages above are computed over")


class SourceBreakdownRow(BaseModel):
    source: str = Field(description='The lead\'s free-text Lead.source value, or "Unknown" if never set')
    leads_touched: int
    conversion_rate_pct: float | None


class SourceAgg(BaseModel):
    """Conversion by lead source/channel (ROADMAP.md C4 — "which lead
    source converts"). Lead.source stays free text (no fixed taxonomy is
    enforced); this groups by whatever string value is actually present,
    bucketing untagged leads under "Unknown" rather than dropping them."""

    by_source: list[SourceBreakdownRow]


class LostReasonBreakdownRow(BaseModel):
    reason: LostReason
    count: int
    pct: float


class LostReasonAgg(BaseModel):
    """Why lost leads were lost (ROADMAP.md C3, doc section 17).
    Current-snapshot semantics like ClosingAgg.lost_leads, not period-scoped
    like ConversionAgg — counts leads currently at stage=lost with a reason
    recorded, regardless of when they were lost. A lead lost without a
    reason recorded (pre-C3 data, or a manager who skipped the field) is
    counted in ClosingAgg.lost_leads but not here — total_lost_with_reason
    can be lower than ClosingAgg.lost_leads for that reason."""

    total_lost_with_reason: int
    by_reason: list[LostReasonBreakdownRow]


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


class PerformanceMetrics(BaseModel):
    """Shared shape for every level of the CALL -> AGENT -> TEAM ->
    ORGANIZATION rollup (ROADMAP.md Phase B) — identical aggregation math
    (app/performance_metrics.py), applied to a different population of
    calls/leads at each level: one agent's calls, one team's agents' calls,
    or every call in the org. Identity (whose numbers these are) and peer
    comparison (benchmark vs. leaderboard) differ per level and live on the
    subclasses below, not here.

    Everything here is computed from data the app already has, plus
    manually-tagged outcomes — see app/agent_performance.py's module
    docstring for what's deliberately not modeled (dialer call volume,
    itemized discovery fields)."""

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
    calls_to_close: CallsToCloseAgg
    lost_reasons: LostReasonAgg
    source_breakdown: SourceAgg

    quality_distribution: list[QualityBucket]
    consistency_score: float | None = Field(description="100 minus the normalized stdev of per-call overall_score; higher = more stable")

    trend: list[TrendPoint]
    strengths: list[StrengthWeakness]
    weaknesses: list[StrengthWeakness]
    coaching_recommendations: list[CoachingRecommendation]

    quality_outcome_matrix: QualityOutcomeQuadrant | None

    notes: list[str] = Field(
        default_factory=list, description="Explicit call-outs for what the source doc asked for that isn't computed here, and why"
    )


class AgentPerformanceReport(PerformanceMetrics):
    agent_id: str
    agent_name: str
    team_id: str | None
    team_name: str | None
    team_benchmark: list[BenchmarkRow]


class LeaderboardRow(BaseModel):
    """One row in an agent-within-team or team-within-org leaderboard."""

    id: str
    name: str
    overall_score: float | None
    conversion_rate_pct: float | None
    calls_analyzed: int


class TeamPerformanceReport(PerformanceMetrics):
    team_id: str
    team_name: str
    manager_agent_id: str | None
    manager_name: str | None
    agent_leaderboard: list[LeaderboardRow]
    org_benchmark: list[BenchmarkRow] = Field(description="This team's numbers vs. the average of every other team in the org")


class OrgPerformanceReport(PerformanceMetrics):
    team_leaderboard: list[LeaderboardRow]
