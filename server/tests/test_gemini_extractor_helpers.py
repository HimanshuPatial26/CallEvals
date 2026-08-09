from google import genai
from google.genai import _transformers

from app.extraction.common import WireExtractionResult, format_transcript, resolve_timestamp, sanitize_wire_payload
from app.schemas import Speaker, TranscriptSegment

TRANSCRIPT = [
    TranscriptSegment(speaker=Speaker.REP, start=0.0, end=2.0, text="Hi there"),
    TranscriptSegment(speaker=Speaker.CUSTOMER, start=2.5, end=5.0, text="It's too expensive"),
]


def test_format_transcript_includes_index_and_speaker():
    formatted = format_transcript(TRANSCRIPT)
    assert "[0] rep" in formatted
    assert "[1] customer" in formatted
    assert "too expensive" in formatted


def test_resolve_timestamp_looks_up_segment_start():
    assert resolve_timestamp(1, TRANSCRIPT) == 2.5


def test_resolve_timestamp_returns_none_for_missing_index():
    assert resolve_timestamp(None, TRANSCRIPT) is None
    assert resolve_timestamp(99, TRANSCRIPT) is None


def test_wire_schema_is_gemini_compatible():
    """Regression test: google-genai<2.0 turns nested Pydantic models into a
    JSON schema with $ref/$defs, which Gemini's structured-output API rejects
    outright (every real extraction call failed with a pydantic
    ValidationError before the SDK was upgraded to 2.17.0 in requirements.txt).
    No network call — this only exercises the SDK's local schema transform,
    which is what actually broke.
    """
    client = genai.Client(api_key="dummy-key-no-network-call")
    schema = _transformers.t_schema(client._api_client, WireExtractionResult)
    assert schema is not None


def _objection(category, quote="q"):
    return {"category": category, "quote": quote, "source_segment_index": None, "confidence": 0.9, "addressed": True}


def test_sanitize_wire_payload_drops_out_of_taxonomy_category():
    """Production incident: an extractor returned category='taxes', which
    isn't one of the 10 fixed ObjectionCategory values. Before this fix,
    that failed the entire call's WireExtractionResult validation -- summary,
    score breakdown, next steps, and the other (valid) objections all lost
    along with it. The fix drops only the offending objection."""
    data = {"objections": [_objection("price"), _objection("taxes"), _objection("timing")]}
    cleaned = sanitize_wire_payload(data)
    assert [o["category"] for o in cleaned["objections"]] == ["price", "timing"]


def test_sanitize_wire_payload_normalizes_case():
    data = {"objections": [_objection("Price")]}
    cleaned = sanitize_wire_payload(data)
    assert cleaned["objections"][0]["category"] == "price"


def test_sanitize_wire_payload_keeps_payload_unchanged_when_all_valid():
    data = {"objections": [_objection("price"), _objection("competitor")], "summary": "s"}
    cleaned = sanitize_wire_payload(data)
    assert cleaned == data


def test_sanitize_wire_payload_tolerates_missing_or_non_list_objections():
    assert sanitize_wire_payload({"summary": "s"}) == {"summary": "s"}
    assert sanitize_wire_payload({"objections": None}) == {"objections": None}


def test_sanitize_wire_payload_lets_a_bad_category_payload_validate():
    """End-to-end regression for the reported bug: a full wire payload with
    one out-of-taxonomy objection now validates successfully instead of
    raising, and the valid objection survives."""
    payload = {
        "summary": "s",
        "next_steps": [],
        "objections": [_objection("taxes"), _objection("price", quote="too expensive")],
        "sentiment": {
            "overall": "neutral",
            "beginning": "neutral",
            "middle": "neutral",
            "end": "neutral",
            "signals": [],
            "confidence": 0.5,
        },
        "buying_intent": {"level": "medium", "signals": [], "follow_up_priority": "soon", "confidence": 0.5},
        "coaching": {
            "top_strength": "a",
            "top_weakness": "b",
            "behavior_to_stop": "c",
            "behavior_to_continue": "d",
            "behavior_to_start": "e",
        },
        "score_breakdown": {
            dim: {"score": 1.0, "max_score": 10.0, "evidence": "ev"}
            for dim in (
                "opening_rapport",
                "discovery_qualification",
                "active_listening",
                "pitch_value_prop",
                "objection_handling",
                "communication_professionalism",
                "closing_next_steps",
            )
        },
    }
    wire = WireExtractionResult.model_validate(sanitize_wire_payload(payload))
    assert len(wire.objections) == 1
    assert wire.objections[0].quote == "too expensive"
