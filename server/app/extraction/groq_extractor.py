"""Extraction via Groq's OpenAI-compatible chat completions API — an
alternative to Gemini for teams hitting Gemini's free-tier cap (20
requests/day per project/model; see ROADMAP.md's "one blocker that isn't a
code task"). Groq's free tier is far more generous on request volume, at
the cost of using an open-weight model (Llama) instead of Gemini for the
same structured-extraction task — expect more prompt-tuning and a lower
precision bar than the Gemini eval numbers in README.md until this path
gets its own precision run.

Prompt, wire schema, and Wire -> ExtractionResult mapping are shared with
GeminiExtractor via app/extraction/common.py — this module is just the
Groq-specific API call and response parsing.

Groq's chat completions API doesn't offer Gemini's native `response_schema`
structured-output mode (a schema the model is constrained to at decode
time); JSON mode (`response_format: {"type": "json_object"}`) only
guarantees the response *parses* as JSON, not that it matches this shape.
Pydantic validation against WireExtractionResult is what actually enforces
the schema here — a shape-mismatched response fails loudly as a
ValidationError instead of silently becoming wrong data. Uses plain httpx
(already a dependency, same pattern as app/asr/deepgram_provider.py)
instead of pulling in the groq/openai SDK for one endpoint.

On a non-2xx response, the error raised includes the response body, not
just the status code — Groq puts the actionable detail there (e.g. a 404
with `"code": "model_decommissioned"` when GROQ_MODEL names a retired
model, which otherwise reads identically to a wrong-URL 404). Groq rotates
model ids over time; check https://console.groq.com/docs/models for the
current list rather than trusting .env.example's default forever.
"""

import json

import httpx

from app.config import settings
from app.extraction.base import ExtractionProvider
from app.extraction.common import EXTRACTION_PROMPT, WireExtractionResult, format_transcript, wire_to_extraction_result
from app.schemas import ExtractionResult, TranscriptSegment

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"

# Groq has no schema-constrained decoding to fall back on, so the prompt
# spells out the exact JSON shape expected in addition to the field-by-field
# instructions in EXTRACTION_PROMPT -- this is belt-and-suspenders for an
# open-weight model, not needed for Gemini's response_schema mode.
_JSON_SHAPE_REMINDER = """
Respond with a single JSON object only -- no prose before or after, no markdown \
code fences -- with exactly this shape:
{
  "summary": "string",
  "next_steps": [{"description": "string", "owner": "rep or customer", "due": "string or null", "source_segment_index": "int or null", "confidence": "float 0-1"}],
  "objections": [{"category": "one of price/timing/competitor/need/trust/authority/product/implementation/contract/switching_cost", "quote": "string", "source_segment_index": "int or null", "confidence": "float 0-1", "addressed": "bool"}],
  "sentiment": {"overall": "positive/neutral/negative", "beginning": "positive/neutral/negative", "middle": "positive/neutral/negative", "end": "positive/neutral/negative", "signals": ["string"], "confidence": "float 0-1"},
  "buying_intent": {"level": "high/medium/low", "signals": ["string"], "follow_up_priority": "string", "confidence": "float 0-1"},
  "coaching": {"top_strength": "string", "top_weakness": "string", "behavior_to_stop": "string", "behavior_to_continue": "string", "behavior_to_start": "string"},
  "score_breakdown": {
    "opening_rapport": {"score": "float 0-10", "max_score": 10, "evidence": "string"},
    "discovery_qualification": {"score": "float 0-20", "max_score": 20, "evidence": "string"},
    "active_listening": {"score": "float 0-10", "max_score": 10, "evidence": "string"},
    "pitch_value_prop": {"score": "float 0-15", "max_score": 15, "evidence": "string"},
    "objection_handling": {"score": "float 0-15", "max_score": 15, "evidence": "string"},
    "communication_professionalism": {"score": "float 0-10", "max_score": 10, "evidence": "string"},
    "closing_next_steps": {"score": "float 0-15", "max_score": 15, "evidence": "string"}
  }
}
"""


class GroqExtractor(ExtractionProvider):
    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys "
                "and put it in server/.env (see .env.example)."
            )

    def extract(self, transcript: list[TranscriptSegment]) -> ExtractionResult:
        prompt = EXTRACTION_PROMPT.format(transcript=format_transcript(transcript)) + _JSON_SHAPE_REMINDER
        response = httpx.post(
            GROQ_CHAT_COMPLETIONS_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
            timeout=60.0,
        )
        if response.is_error:
            # response.raise_for_status() alone drops the response body --
            # exactly the part that says *why* (e.g. Groq returns 404 with a
            # "model_decommissioned" body for a retired model id, which
            # reads identically to a wrong-URL 404 without this).
            raise RuntimeError(f"Groq API error {response.status_code} calling {GROQ_CHAT_COMPLETIONS_URL}: {response.text}")
        content = response.json()["choices"][0]["message"]["content"]
        wire = WireExtractionResult.model_validate(json.loads(content))
        return wire_to_extraction_result(wire, transcript)
