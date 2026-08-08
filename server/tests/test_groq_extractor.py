import json

import httpx
import pytest
from pydantic import ValidationError

from app.config import settings
from app.schemas import Speaker, TranscriptSegment

TRANSCRIPT = [
    TranscriptSegment(speaker=Speaker.REP, start=0.0, end=2.0, text="Hi there"),
    TranscriptSegment(speaker=Speaker.CUSTOMER, start=2.5, end=5.0, text="It's too expensive"),
]

_VALID_WIRE_PAYLOAD = {
    "summary": "Customer interested but price-sensitive.",
    "next_steps": [
        {"description": "Send pricing sheet", "owner": "rep", "due": "tomorrow", "source_segment_index": 0, "confidence": 0.9}
    ],
    "objections": [
        {"category": "price", "quote": "It's too expensive", "source_segment_index": 1, "confidence": 0.9, "addressed": False}
    ],
    "sentiment": {
        "overall": "neutral",
        "beginning": "positive",
        "middle": "neutral",
        "end": "negative",
        "signals": ["hesitation on price"],
        "confidence": 0.8,
    },
    "buying_intent": {"level": "medium", "signals": ["asked about price"], "follow_up_priority": "this week", "confidence": 0.7},
    "coaching": {
        "top_strength": "clear opening",
        "top_weakness": "rushed the pitch",
        "behavior_to_stop": "talking over the customer",
        "behavior_to_continue": "asking open questions",
        "behavior_to_start": "confirming budget early",
    },
    "score_breakdown": {
        "opening_rapport": {"score": 8, "max_score": 10, "evidence": "greeted warmly"},
        "discovery_qualification": {"score": 15, "max_score": 20, "evidence": "asked about timeline"},
        "active_listening": {"score": 7, "max_score": 10, "evidence": "responded to concerns"},
        "pitch_value_prop": {"score": 10, "max_score": 15, "evidence": "tied features to need"},
        "objection_handling": {"score": 5, "max_score": 15, "evidence": "did not address price objection"},
        "communication_professionalism": {"score": 9, "max_score": 10, "evidence": "clear and respectful"},
        "closing_next_steps": {"score": 12, "max_score": 15, "evidence": "proposed a specific follow-up"},
    },
}


@pytest.fixture
def groq_key(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")


def _mock_response(monkeypatch, content: str, status_code: int = 200):
    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(
            status_code, request=request, json={"choices": [{"message": {"content": content}}]}
        )

    monkeypatch.setattr(httpx, "post", fake_post)


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "")
    from app.extraction.groq_extractor import GroqExtractor

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        GroqExtractor()


def test_successful_extraction_maps_to_extraction_result(groq_key, monkeypatch):
    from app.extraction.groq_extractor import GroqExtractor

    _mock_response(monkeypatch, json.dumps(_VALID_WIRE_PAYLOAD))

    result = GroqExtractor().extract(TRANSCRIPT)

    assert result.summary == "Customer interested but price-sensitive."
    assert result.next_steps[0].description == "Send pricing sheet"
    assert result.next_steps[0].source_timestamp == 0.0  # resolved from segment index 0
    assert result.objections[0].quote == "It's too expensive"
    assert result.objections[0].source_timestamp == 2.5  # resolved from segment index 1
    assert result.sentiment.overall.value == "neutral"
    assert result.buying_intent.level.value == "medium"
    assert result.score_breakdown.opening_rapport.score == 8


def test_request_sends_configured_model_and_json_mode(groq_key, monkeypatch):
    # Arbitrary test value -- just confirms whatever's configured flows
    # through to the request, not a recommendation for a real model id.
    monkeypatch.setattr(settings, "groq_model", "test-model-id")
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        request = httpx.Request("POST", url)
        return httpx.Response(
            200, request=request, json={"choices": [{"message": {"content": json.dumps(_VALID_WIRE_PAYLOAD)}}]}
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    from app.extraction.groq_extractor import GroqExtractor

    GroqExtractor().extract(TRANSCRIPT)

    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "test-model-id"
    assert captured["json"]["response_format"] == {"type": "json_object"}


def test_malformed_json_content_raises(groq_key, monkeypatch):
    from app.extraction.groq_extractor import GroqExtractor

    _mock_response(monkeypatch, "not valid json at all")

    with pytest.raises(json.JSONDecodeError):
        GroqExtractor().extract(TRANSCRIPT)


def test_json_not_matching_wire_shape_raises_validation_error(groq_key, monkeypatch):
    from app.extraction.groq_extractor import GroqExtractor

    _mock_response(monkeypatch, json.dumps({"summary": "only a summary, missing everything else"}))

    with pytest.raises(ValidationError):
        GroqExtractor().extract(TRANSCRIPT)


def test_http_error_status_propagates(groq_key, monkeypatch):
    """Regression test: response.raise_for_status() alone raises with only
    the status code in the message, dropping the response body -- which is
    exactly where Groq puts the actionable detail (e.g. "model
    decommissioned" for a retired model id). The error message must
    include the body, not just the status."""
    from app.extraction.groq_extractor import GroqExtractor

    _mock_response(monkeypatch, '{"error": {"message": "model decommissioned", "code": "model_decommissioned"}}', status_code=404)

    with pytest.raises(RuntimeError, match="model_decommissioned"):
        GroqExtractor().extract(TRANSCRIPT)
