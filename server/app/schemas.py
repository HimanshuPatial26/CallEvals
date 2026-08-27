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


class ReviewFeedback(BaseModel):
    """Manager confirm/reject on an extracted next step or objection.

    This is the raw signal behind the A1 extraction-precision metric (PRD section 6) —
    every confirm/reject a manager clicks is one labeled data point.
    """

    item_type: str = Field(description="'next_step' or 'objection'")
    item_index: int
    confirmed: bool


class ConversationShape(BaseModel):
    """Signals computed directly from transcript timing/text — no LLM call, nothing
    invented. Sentiment is a lexicon heuristic, not a validated model; PRD section 5
    explicitly cut sentiment analysis as low-precision, so it is surfaced here as
    unscored context only (see rollups.py / analysis.py), never fed into a flag or
    the (disabled) composite score.
    """

    talk_ratio_rep: float = Field(ge=0.0, le=1.0, description="Share of speaking time that is the rep's")
    questions_asked_rep: int
    longest_rep_turn: float = Field(description="Seconds")
    words_per_minute: float
    sentiment_curve: list[float] = Field(description="Heuristic polarity, -1..1, bucketed across the call")
    sentiment_label: str


class BehaviorFlags(BaseModel):
    """Rule-based, not ML-scored — thresholds mirror the rubric's own configured
    rules (see RubricSettings.flags / analysis.py), so what's editable in Settings
    is exactly what gets computed.
    """

    monologue: bool
    no_discovery_question: bool
    no_dated_next_step: bool
    missing_disclosure: bool
    discount_offered_first: bool


class Agent(BaseModel):
    id: str
    name: str
    team: str = "Corniche"


class Lead(BaseModel):
    id: str
    name: str
    phone: str
    unit: str | None = None
    budget: str | None = None
    stage: str = Field(default="New", description="New | Nurture | Comparing | Viewing done | Offer — manager-set")
    source: str | None = None
    crm_ref: str | None = None
    created_at: datetime


class RubricWeights(BaseModel):
    discovery: int = 25
    objection: int = 25
    listening: int = 20
    nextstep: int = 20
    compliance: int = 10


class FlagToggles(BaseModel):
    monologue: bool = True
    no_discovery_question: bool = True
    no_dated_next_step: bool = True
    missing_disclosure: bool = True
    discount_offered_first: bool = False


class RubricSettings(BaseModel):
    """Single org-wide record — Phase 0 has no multi-tenancy (see storage.py)."""

    weights: RubricWeights = Field(default_factory=RubricWeights)
    flags: FlagToggles = Field(default_factory=FlagToggles)
    objection_tags: list[str] = Field(default_factory=lambda: ["price", "timing", "competitor"])
    surface_threshold: int = Field(default=70, description="Below this confidence %, an extraction is stored but not shown")
    autoflag_threshold: int = Field(default=88, description="Above this confidence %, an item skips manager confirmation")
    digest: str = Field(default="Daily", description="Daily | Weekly | Off")
    retention_days: int = 180
    rep_private_mode: bool = True
    composite_score_enabled: bool = Field(
        default=False,
        description="PRD section 5 deliberately cut the composite score. Off by default; "
        "no scoring pipeline exists to back it even when on.",
    )


class CallRecord(BaseModel):
    id: str
    filename: str
    dual_channel: bool
    created_at: datetime
    agent_id: str | None = None
    lead_id: str | None = None
    duration: float | None = Field(default=None, description="Seconds, derived from transcript once ASR completes")
    speaker_source: str | None = Field(
        default=None,
        description="How rep/customer were identified: channel_split (hard separation, "
        "most trustworthy) | diarization (voice-clustering heuristic, can be wrong) | "
        "unknown (no separation available) — see app/asr/base.py",
    )
    transcript: list[TranscriptSegment] = Field(default_factory=list)
    extraction: ExtractionResult | None = None
    shape: ConversationShape | None = None
    flags: BehaviorFlags | None = None
    feedback: list[ReviewFeedback] = Field(default_factory=list)
    status: str = Field(default="processing", description="processing | done | failed")
    error: str | None = None
    first_viewed_at: datetime | None = Field(default=None, description="Set on first GET of this call's detail — backs the manager-engagement metric")
