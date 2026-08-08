from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Speaker(str, Enum):
    REP = "rep"
    CUSTOMER = "customer"
    UNKNOWN = "unknown"


class ObjectionCategory(str, Enum):
    """F4 — deliberately three categories, not five. See PRD section 5."""

    PRICE = "price"
    TIMING = "timing"
    COMPETITOR = "competitor"


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


class ExtractionResult(BaseModel):
    """F2 + F3 + F4 combined — the LLM extraction step's output shape."""

    summary: str = Field(description="Under 150 words per PRD F2")
    next_steps: list[NextStep] = Field(default_factory=list)
    objections: list[Objection] = Field(default_factory=list)


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
    feedback: list[ReviewFeedback] = Field(default_factory=list)
    status: str = Field(default="processing", description="processing | done | failed")
    error: str | None = None
