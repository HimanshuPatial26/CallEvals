from app.extraction.gemini_extractor import _format_transcript, _resolve_timestamp
from app.schemas import Speaker, TranscriptSegment

TRANSCRIPT = [
    TranscriptSegment(speaker=Speaker.REP, start=0.0, end=2.0, text="Hi there"),
    TranscriptSegment(speaker=Speaker.CUSTOMER, start=2.5, end=5.0, text="It's too expensive"),
]


def test_format_transcript_includes_index_and_speaker():
    formatted = _format_transcript(TRANSCRIPT)
    assert "[0] rep" in formatted
    assert "[1] customer" in formatted
    assert "too expensive" in formatted


def test_resolve_timestamp_looks_up_segment_start():
    assert _resolve_timestamp(1, TRANSCRIPT) == 2.5


def test_resolve_timestamp_returns_none_for_missing_index():
    assert _resolve_timestamp(None, TRANSCRIPT) is None
    assert _resolve_timestamp(99, TRANSCRIPT) is None
