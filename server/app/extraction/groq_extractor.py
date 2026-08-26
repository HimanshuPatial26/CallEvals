"""Extraction via Groq's OpenAI-compatible chat completions API. Opt-in
(EXTRACTION_PROVIDER=groq in .env) — Gemini stays the default extraction path.

Uses a plain httpx call rather than the `groq` SDK, matching how
app/asr/deepgram_provider.py talks to Deepgram directly: one more REST call, not
one more SDK dependency, for an API this small.

Unlike Gemini's response_schema (a real structured-output constraint enforced by
the API), Groq's response_format={"type": "json_object"} only guarantees the reply
parses as JSON, not that it matches a specific shape — so the target shape has to
be spelled out in the prompt, and the result is worth validating strictly against
WireExtractionResult before anything downstream trusts it. A model that returns
well-formed but wrong-shaped JSON fails loudly as a pydantic ValidationError,
surfaced to the review UI via app/pipeline.py's broad exception handling, same as
any other extraction failure.
"""

import httpx

from app.config import settings
from app.extraction.base import ExtractionProvider
from app.extraction.wire import WireExtractionResult, format_transcript, resolve_timestamp
from app.schemas import ExtractionResult, NextStep, Objection, TranscriptSegment

_API_URL = "https://api.groq.com/openai/v1/chat/completions"

EXTRACTION_PROMPT = """You are analyzing a sales call transcript for a real-estate \
brokerage sales manager. Extract exactly three things:

1. summary: under 150 words. What the customer wants, budget signals, timeline, \
   and current state of the deal.
2. next_steps: what the rep committed to and by when. Only include commitments \
   actually stated on the call — do not infer ones that weren't said. If the rep \
   states a commitment and the customer separately acknowledges or restates it \
   (e.g. rep says "I'll send the offer letter tomorrow", customer says "I'll look \
   out for it"), that is ONE next step, not two — extract it once, attributed to \
   whoever owns the action.
3. objections: only from these three categories: price, timing, competitor. Quote \
   the customer's own words, don't paraphrase. Skip anything that doesn't clearly \
   fit one of the three categories. If the customer raises the same underlying \
   concern more than once in the call, even in different words (e.g. restating a \
   price concern after first mentioning it), that is ONE objection, not two — pick \
   the clearest quote and extract it once.

Before finalizing, check your own next_steps and objections lists: if two entries \
describe the same underlying commitment or the same underlying concern, merge them \
into one. A manager reviewing this expects each real thing that happened on the \
call to appear exactly once, not fragmented across near-duplicate entries.

For every next step and objection, set source_segment_index to the index of the \
transcript segment (shown in brackets below) it came from. Use null if you can't \
tie it to one segment.

Respond with a single JSON object and nothing else — no markdown fences, no \
commentary — matching exactly this shape:
{{
  "summary": "<string, under 150 words>",
  "next_steps": [
    {{
      "description": "<string>",
      "owner": "<rep | customer | unknown>",
      "due": "<string or null>",
      "source_segment_index": <integer or null>,
      "confidence": <number between 0 and 1>
    }}
  ],
  "objections": [
    {{
      "category": "<price | timing | competitor>",
      "quote": "<string, the customer's own words>",
      "source_segment_index": <integer or null>,
      "confidence": <number between 0 and 1>
    }}
  ]
}}
Omit nothing from the shape above, and use empty lists rather than omitting keys \
when there are no next steps or objections.

Transcript:
{transcript}
"""


def _error_guidance(response: httpx.Response) -> str:
    """Groq's error 'code' pins down what actually went wrong more precisely
    than the status code alone — worth translating the ones with a known,
    actionable cause into something a manager reading the failed-call error
    doesn't have to go look up.
    """
    try:
        code = response.json().get("error", {}).get("code")
    except Exception:  # noqa: BLE001 — a malformed error body just means no extra guidance
        return ""
    if code == "json_validate_failed":
        return (
            " Groq accepted the request but the model's own output failed Groq's JSON "
            "validation — this usually means the model returned empty or non-JSON content "
            "under response_format=json_object (some models, especially reasoning-enabled "
            "ones, don't handle strict JSON mode reliably). Try a well-established "
            "non-reasoning model for GROQ_MODEL, e.g. llama-3.3-70b-versatile."
        )
    if code == "rate_limit_exceeded":
        return (
            " This is an account-level tokens-per-minute cap for this model on your Groq "
            "tier, not something a retry or a smaller max_completion_tokens fully solves for "
            "a genuinely long call — the transcript itself is most of the request size. Two "
            "options: switch GROQ_MODEL to a smaller/faster model (these typically get a much "
            "higher free-tier TPM allowance than a larger model — llama-3.1-8b-instant is "
            "worth trying), or raise the limit on the tier this key is on at "
            "https://console.groq.com/settings/billing."
        )
    return ""


class GroqExtractor(ExtractionProvider):
    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "EXTRACTION_PROVIDER=groq but GROQ_API_KEY is not set. Get a free-credit "
                "key at https://console.groq.com and put it in server/.env (see .env.example)."
            )

    def extract(self, transcript: list[TranscriptSegment]) -> ExtractionResult:
        prompt = EXTRACTION_PROMPT.format(transcript=format_transcript(transcript))
        response = httpx.post(
            _API_URL,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                # Without an explicit cap, a long call (many next steps/objections)
                # can get truncated mid-JSON, which is one way to land exactly on
                # Groq's json_validate_failed error below. Kept modest rather than
                # generous — Groq's per-minute token limit counts this against the
                # request's total (see _error_guidance's rate_limit_exceeded case),
                # and F2-F4 output is inherently compact structured data, not prose.
                "max_completion_tokens": 1536,
            },
            timeout=120.0,
        )
        if response.is_error:
            # httpx's default raise_for_status() message drops the response body,
            # which is where Groq (OpenAI-compatible) actually puts the reason —
            # e.g. an invalid/retired GROQ_MODEL, or a request field it rejects.
            raise RuntimeError(f"Groq extraction request failed ({response.status_code}): {response.text}{_error_guidance(response)}")
        content = response.json()["choices"][0]["message"]["content"]
        wire = WireExtractionResult.model_validate_json(content)

        return ExtractionResult(
            summary=wire.summary,
            next_steps=[
                NextStep(
                    description=ns.description,
                    owner=ns.owner,
                    due=ns.due,
                    source_timestamp=resolve_timestamp(ns.source_segment_index, transcript),
                    confidence=ns.confidence,
                )
                for ns in wire.next_steps
            ],
            objections=[
                Objection(
                    category=obj.category,
                    quote=obj.quote,
                    source_timestamp=resolve_timestamp(obj.source_segment_index, transcript),
                    confidence=obj.confidence,
                )
                for obj in wire.objections
            ],
        )
