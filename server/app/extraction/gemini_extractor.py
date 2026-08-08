"""Extraction via the Gemini Developer API free tier (ai.google.dev) — no GCP billing
account required, unlike Cloud STT/Vertex. Structured JSON output constrains the
model to the F2/F3/F4 shape instead of parsing free text.

Prompt, wire schema, and Wire -> ExtractionResult mapping live in
app/extraction/common.py, shared with every other ExtractionProvider — this
module is just the Gemini-specific API call and response parsing.
"""

import json

from google import genai
from google.genai import types

from app.config import settings
from app.extraction.base import ExtractionProvider
from app.extraction.common import EXTRACTION_PROMPT, WireExtractionResult, format_transcript, wire_to_extraction_result
from app.schemas import ExtractionResult, TranscriptSegment


class GeminiExtractor(ExtractionProvider):
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at https://ai.google.dev "
                "and put it in server/.env (see .env.example)."
            )
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def extract(self, transcript: list[TranscriptSegment]) -> ExtractionResult:
        prompt = EXTRACTION_PROMPT.format(transcript=format_transcript(transcript))
        response = self._client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WireExtractionResult,
            ),
        )

        wire = response.parsed
        if wire is None:
            wire = WireExtractionResult.model_validate(json.loads(response.text))

        return wire_to_extraction_result(wire, transcript)
