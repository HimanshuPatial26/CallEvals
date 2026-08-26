"""Extraction via Groq's OpenAI-compatible chat completions API — an
alternative to Gemini for teams hitting Gemini's free-tier cap (20
requests/day per project/model; see ROADMAP.md's "one blocker that isn't a
code task"). Groq's free tier is far more generous on request volume, at
the cost of using an open-weight model instead of Gemini for the same
structured-extraction task — expect more prompt-tuning and a lower
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
ValidationError instead of silently becoming wrong data, EXCEPT for
objection categories: sanitize_wire_payload (common.py) drops any
objection whose category falls outside the fixed taxonomy before
validation runs, rather than failing the whole extraction over it. Hit in
production: an open-weight model invented category='taxes', which isn't
one of the 10 the prompt asks for, and the entire call (summary, score,
next steps, every other objection) was being discarded over that one
field. Uses plain httpx (already a dependency, same pattern as
app/asr/deepgram_provider.py) instead of pulling in the groq/openai SDK
for one endpoint.

On a non-2xx response, the error raised includes the response body, not
just the status code — Groq puts the actionable detail there (e.g. a 404
with `"code": "model_decommissioned"` when GROQ_MODEL names a retired
model, which otherwise reads identically to a wrong-URL 404). This is
exactly what happened in production: the original default here,
llama-3.3-70b-versatile, got decommissioned by Groq and started 404ing.
Confirmed and fixed by a user against the real API — this dev environment
can't reach api.groq.com or console.groq.com at all (egress-blocked), so
it can't independently verify Groq model ids. GROQ_MODEL now defaults to
openai/gpt-oss-120b, confirmed live as of 2026-08-08, but Groq rotates
model ids over time regardless; check
https://console.groq.com/docs/models if this one goes stale too.

Third production incident: not every Groq-hosted model supports
`response_format: {"type": "json_object"}` at all -- some (reasoning /
preview models in particular) 400 outright with `"param":
"response_format"` when it's included, rather than just ignoring it.
Failing the whole call over a request option the model doesn't support,
when the prompt already spells out the exact JSON shape as a fallback
(see _JSON_SHAPE_REMINDER), was pure lost value -- so on that specific
400, the request is retried once without response_format instead of
raising. Without JSON mode a model is slightly more likely to wrap its
answer in a ```json fence despite being told not to, so the response is
unwrapped before parsing; Pydantic validation against WireExtractionResult
is still what actually enforces the shape either way.

Fourth production incident: a call whose transcript (plus the extraction
prompt) exceeded GROQ_MODEL's context window got Groq's generic 400
`"Please reduce the length of the messages or completion."` -- which
doesn't say why. Unlike the other three incidents this isn't a code bug,
it's a genuine capacity limit, and no truncation is attempted: silently
dropping transcript content to fit would risk confidently-wrong analytics
from a partial call with no signal to the reviewer that anything was cut.
Detected specifically (400, `error.param == "messages"`, message mentions
"reduce the length") and re-raised with what's actually going on and what
to do about it (a Groq model with a larger context window, or a shorter
recording) instead of Groq's unexplained generic message.

Fifth production incident, and a different kind of limit: a 413 (not the
more usual 429) with `"code": "rate_limit_exceeded"`, `"type": "tokens"`
-- an org-wide tokens-per-minute cap on the free/on-demand tier, not a
per-request context-window ceiling. This one genuinely is transient (the
cap is a rolling per-minute window), so the re-raised message says so
explicitly rather than reading like the same dead end as the context-
window case. No automatic wait-and-retry is attempted here either --
this environment can't verify Groq's actual reset timing or rate-limit
headers against the real API, and a blind sleep in the request path is a
bigger behavior change than a message improvement should make on its
own judgment.
"""

import json
import re

import httpx

from app.config import settings
from app.extraction.base import ExtractionProvider
from app.extraction.common import (
    EXTRACTION_PROMPT,
    WireExtractionResult,
    format_transcript,
    sanitize_wire_payload,
    wire_to_extraction_result,
)
from app.schemas import ExtractionResult, TranscriptSegment

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"

# Groq has no schema-constrained decoding to fall back on, so the prompt
# spells out the exact JSON shape expected in addition to the field-by-field
# instructions in EXTRACTION_PROMPT -- this is belt-and-suspenders for an
# open-weight model, not needed for Gemini's response_schema mode.
#
# Minified (no pretty-print whitespace) rather than the original indented
# form -- shaved ~300 chars / a rough 80 tokens off *every* Groq request's
# fixed overhead after a real account hit its tokens-per-minute cap by only
# 231 tokens (see README's "Sixth incident"). Not a fix for that class of
# problem on its own (an account already well over its TPM budget needs a
# different model/tier or fewer tokens elsewhere, e.g. a shorter
# transcript), but free headroom for exactly the "just barely over" case.
_JSON_SHAPE_REMINDER = (
    "Respond with one JSON object only, no prose, no code fences, exactly this shape "
    "(values shown are type hints, not literal): "
    '{"summary":"str","next_steps":[{"description":"str","owner":"rep|customer","due":"str|null",'
    '"source_segment_index":"int|null","confidence":0.0}],"objections":[{"category":'
    '"price|timing|competitor|need|trust|authority|product|implementation|contract|switching_cost",'
    '"quote":"str","source_segment_index":"int|null","confidence":0.0,"addressed":true}],'
    '"sentiment":{"overall":"positive|neutral|negative","beginning":"positive|neutral|negative",'
    '"middle":"positive|neutral|negative","end":"positive|neutral|negative","signals":["str"],'
    '"confidence":0.0},"buying_intent":{"level":"high|medium|low","signals":["str"],'
    '"follow_up_priority":"str","confidence":0.0},"coaching":{"top_strength":"str",'
    '"top_weakness":"str","behavior_to_stop":"str","behavior_to_continue":"str",'
    '"behavior_to_start":"str"},"score_breakdown":{"opening_rapport":{"score":0.0,"max_score":10,'
    '"evidence":"str"},"discovery_qualification":{"score":0.0,"max_score":20,"evidence":"str"},'
    '"active_listening":{"score":0.0,"max_score":10,"evidence":"str"},"pitch_value_prop":'
    '{"score":0.0,"max_score":15,"evidence":"str"},"objection_handling":{"score":0.0,"max_score":15,'
    '"evidence":"str"},"communication_professionalism":{"score":0.0,"max_score":10,"evidence":"str"},'
    '"closing_next_steps":{"score":0.0,"max_score":15,"evidence":"str"}}}'
)


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL)


def _parse_json_object(content: str) -> dict:
    """Models without native JSON mode occasionally wrap the answer in a
    ```json fence despite being told not to (see _JSON_SHAPE_REMINDER) --
    unwrap it before parsing rather than failing the call over formatting."""
    text = content.strip()
    match = _FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def _is_json_mode_unsupported(response: httpx.Response) -> bool:
    if response.status_code != 400:
        return False
    try:
        error = response.json().get("error", {})
    except ValueError:
        return False
    return error.get("param") == "response_format"


def _is_context_length_exceeded(response: httpx.Response) -> bool:
    if response.status_code != 400:
        return False
    try:
        error = response.json().get("error", {})
    except ValueError:
        return False
    return error.get("param") == "messages" and "reduce the length" in error.get("message", "").lower()


def _is_tpm_rate_limited(response: httpx.Response) -> bool:
    # Groq returns 413 (not the more usual 429) for this one.
    if response.status_code != 413:
        return False
    try:
        error = response.json().get("error", {})
    except ValueError:
        return False
    return error.get("code") == "rate_limit_exceeded" and error.get("type") == "tokens"


class GroqExtractor(ExtractionProvider):
    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys "
                "and put it in server/.env (see .env.example)."
            )

    def extract(self, transcript: list[TranscriptSegment]) -> ExtractionResult:
        prompt = EXTRACTION_PROMPT.format(transcript=format_transcript(transcript)) + _JSON_SHAPE_REMINDER
        payload = {
            "model": settings.groq_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        response = self._post({**payload, "response_format": {"type": "json_object"}})
        if response.is_error and _is_json_mode_unsupported(response):
            # Some Groq-hosted models 400 outright on response_format
            # instead of ignoring it -- retry once without it rather than
            # losing the call over a mode the model just doesn't have.
            response = self._post(payload)
        if response.is_error and _is_context_length_exceeded(response):
            # Not a code bug like the other cases here -- a genuine capacity
            # limit. Groq's own message ("Please reduce the length of the
            # messages or completion") doesn't say *why*: this call's
            # transcript plus the extraction prompt is bigger than
            # GROQ_MODEL's context window. No truncation is attempted here
            # -- silently dropping transcript content would risk producing
            # confidently-wrong analytics from a partial call with no
            # signal to the reviewer that anything was cut. Surfaced as an
            # actionable error instead.
            raise RuntimeError(
                f"Groq rejected this call: the transcript plus prompt is too long for "
                f"GROQ_MODEL={settings.groq_model!r}'s context window. Try a Groq model with a "
                f"larger context window (see https://console.groq.com/docs/models for sizes) or "
                f"a shorter recording. Original error: {response.text}"
            )
        if response.is_error and _is_tpm_rate_limited(response):
            # Also not a code bug: a free/on-demand-tier tokens-per-minute
            # cap, shared across the whole org, not just this call -- and
            # unlike the context-window case this one is transient (the
            # cap resets on a rolling per-minute window), so it's worth
            # saying that explicitly rather than making it read like a
            # dead end. No automatic wait-and-retry here either: this
            # environment can't verify Groq's actual reset timing/headers
            # against the real API, and a blind sleep in the request path
            # is a bigger behavior change than this fix should make on its
            # own judgment.
            raise RuntimeError(
                f"Groq's tokens-per-minute rate limit was hit for GROQ_MODEL={settings.groq_model!r} "
                f"(a free/on-demand-tier cap shared across the whole account, not just this call). "
                f"This is usually transient -- wait about a minute and retry. If it keeps happening, "
                f"see https://console.groq.com/settings/billing to raise the limit. "
                f"Original error: {response.text}"
            )
        if response.is_error:
            # response.raise_for_status() alone drops the response body --
            # exactly the part that says *why* (e.g. Groq returns 404 with a
            # "model_decommissioned" body for a retired model id, which
            # reads identically to a wrong-URL 404 without this).
            raise RuntimeError(f"Groq API error {response.status_code} calling {GROQ_CHAT_COMPLETIONS_URL}: {response.text}")
        content = response.json()["choices"][0]["message"]["content"]
        wire = WireExtractionResult.model_validate(sanitize_wire_payload(_parse_json_object(content)))
        return wire_to_extraction_result(wire, transcript)

    def _post(self, payload: dict) -> httpx.Response:
        return httpx.post(
            GROQ_CHAT_COMPLETIONS_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json=payload,
            timeout=60.0,
        )
