"""Extraction via the Gemini Developer API free tier (ai.google.dev) — no GCP billing
account required, unlike Cloud STT/Vertex. Structured JSON output constrains the
model to the F2/F3/F4 shape instead of parsing free text.

Source timestamps are never trusted from the model directly — it points at a
transcript segment *index*, and we look up the real start time locally. LLMs are
unreliable at reproducing numeric timestamps verbatim; segment indices are a
closed, checkable set the model can't hallucinate its way around as easily, and it
keeps the "click through to the transcript" trust mechanism (PRD section 10)
actually accurate.
"""

import json

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import settings
from app.extraction.base import ExtractionProvider
from app.schemas import (
    BuyingIntent,
    Coaching,
    DimensionScore,
    ExtractionResult,
    IntentLevel,
    NextStep,
    Objection,
    ObjectionCategory,
    ScoreBreakdown,
    Sentiment,
    SentimentLabel,
    Speaker,
    TranscriptSegment,
)

EXTRACTION_PROMPT = """You are analyzing a sales call transcript for a real-estate \
brokerage sales manager. Extract the following:

1. summary: under 150 words. What the customer wants, budget signals, timeline, \
   and current state of the deal.
2. next_steps: what the rep committed to and by when. Only include commitments \
   actually stated on the call — do not infer ones that weren't said. If the rep \
   states a commitment and the customer separately acknowledges or restates it \
   (e.g. rep says "I'll send the offer letter tomorrow", customer says "I'll look \
   out for it"), that is ONE next step, not two — extract it once, attributed to \
   whoever owns the action.
3. objections: from these categories only: price, timing, competitor, need, trust, \
   authority, product, implementation, contract, switching_cost. Quote the \
   customer's own words, don't paraphrase. Skip anything that doesn't clearly fit \
   one of these categories. If the customer raises the same underlying concern \
   more than once in the call, even in different words (e.g. restating a price \
   concern after first mentioning it), that is ONE objection, not two — pick the \
   clearest quote and extract it once. Also set addressed: true if the rep \
   responds to the objection later in the call with a relevant answer, offer, or \
   explanation; false if it's raised and the call moves on without the rep coming \
   back to it.
4. sentiment: overall, and separately for the beginning/middle/end thirds of the \
   call, each one of positive/neutral/negative. List 1-4 short signal phrases \
   naming what drove the read (e.g. "hesitation on price", "enthusiasm about \
   move-in timeline"). This is a read on tone, not a fact — set confidence \
   accordingly.
5. buying_intent: an overall level (high/medium/low) from the customer's own \
   statements — questions about timing/cost/next steps signal higher intent than \
   "just looking" language. List the quotes or moments that drove the level, and a \
   short free-text recommended follow-up priority/timing.
6. coaching: one top_strength, one top_weakness, one behavior_to_stop, one \
   behavior_to_continue, one behavior_to_start for the rep, each a single concrete \
   sentence grounded in something that happened on this specific call — not \
   generic sales advice.
7. score_breakdown: score these seven dimensions of the rep's performance on THIS \
   call, each out of its stated max, with one sentence of transcript-grounded \
   evidence per score (what did/didn't happen, not a generic justification):
   - opening_rapport (max 10): greeting, introduction, purpose stated, professionalism
   - discovery_qualification (max 20): did the rep uncover need, budget, timeline, \
     decision-maker, pain point, urgency
   - active_listening (max 10): did the rep respond to what the customer actually \
     said, or talk past it
   - pitch_value_prop (max 15): was the pitch relevant to the stated need, features \
     tied to benefits, no unsupported claims
   - objection_handling (max 15): were objections acknowledged and addressed, not \
     dismissed or ignored
   - communication_professionalism (max 10): clarity, pacing, respectful tone
   - closing_next_steps (max 15): did the rep ask for a specific next step / \
     commitment rather than ending vaguely

Before finalizing, check your own next_steps and objections lists: if two entries \
describe the same underlying commitment or the same underlying concern, merge them \
into one. A manager reviewing this expects each real thing that happened on the \
call to appear exactly once, not fragmented across near-duplicate entries.

For every next step and objection, set source_segment_index to the index of the \
transcript segment (shown in brackets below) it came from. Use null if you can't \
tie it to one segment.

Transcript:
{transcript}
"""


class _WireNextStep(BaseModel):
    description: str
    owner: Speaker
    due: str | None = None
    source_segment_index: int | None = None
    confidence: float


class _WireObjection(BaseModel):
    category: ObjectionCategory
    quote: str
    source_segment_index: int | None = None
    confidence: float
    addressed: bool


class _WireSentiment(BaseModel):
    overall: SentimentLabel
    beginning: SentimentLabel
    middle: SentimentLabel
    end: SentimentLabel
    signals: list[str]
    confidence: float


class _WireBuyingIntent(BaseModel):
    level: IntentLevel
    signals: list[str]
    follow_up_priority: str
    confidence: float


class _WireCoaching(BaseModel):
    top_strength: str
    top_weakness: str
    behavior_to_stop: str
    behavior_to_continue: str
    behavior_to_start: str


class _WireDimensionScore(BaseModel):
    score: float
    max_score: float
    evidence: str


class _WireScoreBreakdown(BaseModel):
    opening_rapport: _WireDimensionScore
    discovery_qualification: _WireDimensionScore
    active_listening: _WireDimensionScore
    pitch_value_prop: _WireDimensionScore
    objection_handling: _WireDimensionScore
    communication_professionalism: _WireDimensionScore
    closing_next_steps: _WireDimensionScore


class _WireExtractionResult(BaseModel):
    summary: str
    next_steps: list[_WireNextStep]
    objections: list[_WireObjection]
    sentiment: _WireSentiment
    buying_intent: _WireBuyingIntent
    coaching: _WireCoaching
    score_breakdown: _WireScoreBreakdown


def _format_transcript(transcript: list[TranscriptSegment]) -> str:
    lines = [
        f"[{i}] {seg.speaker.value} ({seg.start:.1f}s-{seg.end:.1f}s): {seg.text}"
        for i, seg in enumerate(transcript)
    ]
    return "\n".join(lines)


def _resolve_timestamp(index: int | None, transcript: list[TranscriptSegment]) -> float | None:
    if index is None or index < 0 or index >= len(transcript):
        return None
    return transcript[index].start


class GeminiExtractor(ExtractionProvider):
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at https://ai.google.dev "
                "and put it in server/.env (see .env.example)."
            )
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def extract(self, transcript: list[TranscriptSegment]) -> ExtractionResult:
        prompt = EXTRACTION_PROMPT.format(transcript=_format_transcript(transcript))
        response = self._client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_WireExtractionResult,
            ),
        )

        wire = response.parsed
        if wire is None:
            wire = _WireExtractionResult.model_validate(json.loads(response.text))

        return ExtractionResult(
            summary=wire.summary,
            next_steps=[
                NextStep(
                    description=ns.description,
                    owner=ns.owner,
                    due=ns.due,
                    source_timestamp=_resolve_timestamp(ns.source_segment_index, transcript),
                    confidence=ns.confidence,
                )
                for ns in wire.next_steps
            ],
            objections=[
                Objection(
                    category=obj.category,
                    quote=obj.quote,
                    source_timestamp=_resolve_timestamp(obj.source_segment_index, transcript),
                    confidence=obj.confidence,
                    addressed=obj.addressed,
                )
                for obj in wire.objections
            ],
            sentiment=Sentiment(
                overall=wire.sentiment.overall,
                beginning=wire.sentiment.beginning,
                middle=wire.sentiment.middle,
                end=wire.sentiment.end,
                signals=wire.sentiment.signals,
                confidence=wire.sentiment.confidence,
            ),
            buying_intent=BuyingIntent(
                level=wire.buying_intent.level,
                signals=wire.buying_intent.signals,
                follow_up_priority=wire.buying_intent.follow_up_priority,
                confidence=wire.buying_intent.confidence,
            ),
            coaching=Coaching(
                top_strength=wire.coaching.top_strength,
                top_weakness=wire.coaching.top_weakness,
                behavior_to_stop=wire.coaching.behavior_to_stop,
                behavior_to_continue=wire.coaching.behavior_to_continue,
                behavior_to_start=wire.coaching.behavior_to_start,
            ),
            score_breakdown=ScoreBreakdown(
                opening_rapport=DimensionScore(**wire.score_breakdown.opening_rapport.model_dump()),
                discovery_qualification=DimensionScore(**wire.score_breakdown.discovery_qualification.model_dump()),
                active_listening=DimensionScore(**wire.score_breakdown.active_listening.model_dump()),
                pitch_value_prop=DimensionScore(**wire.score_breakdown.pitch_value_prop.model_dump()),
                objection_handling=DimensionScore(**wire.score_breakdown.objection_handling.model_dump()),
                communication_professionalism=DimensionScore(
                    **wire.score_breakdown.communication_professionalism.model_dump()
                ),
                closing_next_steps=DimensionScore(**wire.score_breakdown.closing_next_steps.model_dump()),
            ),
        )
