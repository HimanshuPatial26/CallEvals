import json

import httpx
import pytest

from app.config import settings
from app.schemas import Speaker, TranscriptSegment

TRANSCRIPT = [
    TranscriptSegment(speaker=Speaker.REP, start=0.0, end=4.0, text="What's your budget?"),
    TranscriptSegment(speaker=Speaker.CUSTOMER, start=4.5, end=8.0, text="Honestly 2.4 million feels too expensive."),
]


@pytest.fixture
def groq_key(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")


def _mock_chat_completion(monkeypatch, wire_payload):
    class FakeResponse:
        is_error = False

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(wire_payload)}}]}

    captured = {}

    def fake_post(url, *, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    return captured


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "")
    from app.extraction.groq_extractor import GroqExtractor

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        GroqExtractor()


def test_extract_parses_valid_wire_payload(groq_key, monkeypatch):
    from app.extraction.groq_extractor import GroqExtractor

    _mock_chat_completion(
        monkeypatch,
        {
            "summary": "Customer flagged price as a concern.",
            "next_steps": [
                {"description": "Send a revised quote", "owner": "rep", "due": "tomorrow", "source_segment_index": 0, "confidence": 0.9}
            ],
            "objections": [
                {"category": "price", "quote": "too expensive", "source_segment_index": 1, "confidence": 0.85}
            ],
        },
    )

    result = GroqExtractor().extract(TRANSCRIPT)

    assert result.summary == "Customer flagged price as a concern."
    assert result.next_steps[0].owner == Speaker.REP
    assert result.next_steps[0].source_timestamp == 0.0
    assert result.objections[0].category == "price"
    assert result.objections[0].source_timestamp == 4.5


def test_extract_sends_json_mode_and_configured_model(groq_key, monkeypatch):
    from app.extraction.groq_extractor import GroqExtractor

    monkeypatch.setattr(settings, "groq_model", "test-model")
    captured = _mock_chat_completion(monkeypatch, {"summary": "s", "next_steps": [], "objections": []})

    GroqExtractor().extract(TRANSCRIPT)

    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["max_completion_tokens"] > 0


def test_extract_raises_on_malformed_json_response(groq_key, monkeypatch):
    from app.extraction.groq_extractor import GroqExtractor

    class FakeResponse:
        is_error = False

        def json(self):
            return {"choices": [{"message": {"content": "not valid json"}}]}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse())

    with pytest.raises(Exception):  # noqa: B017 — any parse/validation failure is the point
        GroqExtractor().extract(TRANSCRIPT)


def test_extract_surfaces_the_actual_error_body_on_a_4xx(groq_key, monkeypatch):
    """Regression test: httpx's raise_for_status() message drops the response
    body, which is where Groq (OpenAI-compatible) puts the actual reason for a
    400 — e.g. an invalid/retired model. GroqExtractor should surface that text,
    not just the generic '400 Bad Request'."""
    from app.extraction.groq_extractor import GroqExtractor

    class FakeResponse:
        is_error = True
        status_code = 400
        text = '{"error": {"message": "The model `bogus-model` does not exist", "type": "invalid_request_error"}}'

    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse())

    with pytest.raises(RuntimeError, match="does not exist"):
        GroqExtractor().extract(TRANSCRIPT)


def test_extract_adds_guidance_for_json_validate_failed(groq_key, monkeypatch):
    """Reproduces the reported failure: Groq accepts the model and request, but
    the model's own output fails Groq's server-side JSON validation. The raised
    error should point at the likely cause (reasoning-model output under strict
    JSON mode) rather than just echoing Groq's generic message back."""
    from app.extraction.groq_extractor import GroqExtractor

    class FakeResponse:
        is_error = True
        status_code = 400
        text = (
            '{"error": {"message": "Failed to validate JSON. Please adjust your prompt. '
            'See \'failed_generation\' for more details.", "type": "invalid_request_error", '
            '"code": "json_validate_failed", "failed_generation": ""}}'
        )

        def json(self):
            import json as _json

            return _json.loads(self.text)

    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse())

    with pytest.raises(RuntimeError, match="llama-3.3-70b-versatile"):
        GroqExtractor().extract(TRANSCRIPT)
