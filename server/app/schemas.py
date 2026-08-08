from datetime import datetime
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


class CallRecord(BaseModel):
    id: str
    filename: str
    dual_channel: bool
    created_at: datetime
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
