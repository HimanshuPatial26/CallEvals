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
from app.schemas import ExtractionResult, NextStep, Objection, ObjectionCategory, Speaker, TranscriptSegment

EXTRACTION_PROMPT = """You are analyzing a sales call transcript for a real-estate \
brokerage sales manager. Extract exactly three things:

1. summary: under 150 words. What the customer wants, budget signals, timeline, \
   and current state of the deal.
2. next_steps: what the rep committed to and by when. Only include commitments \
   actually stated on the call — do not infer ones that weren't said.
3. objections: only from these three categories: price, timing, competitor. Quote \
   the customer's own words, don't paraphrase. Skip anything that doesn't clearly \
   fit one of the three categories.

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


class _WireExtractionResult(BaseModel):
    summary: str
    next_steps: list[_WireNextStep]
    objections: list[_WireObjection]


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
                )
                for obj in wire.objections
            ],
        )
