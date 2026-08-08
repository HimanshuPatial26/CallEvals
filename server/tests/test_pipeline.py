from datetime import datetime, timezone
from pathlib import Path

from app.asr.base import ASRProvider
from app.extraction.base import ExtractionProvider
from app.pipeline import process_call
from app.schemas import (
    CallRecord,
    ExtractionResult,
    NextStep,
    Speaker,
    TranscriptSegment,
)


class FakeASR(ASRProvider):
    def transcribe(self, audio_path: Path, dual_channel: bool) -> list[TranscriptSegment]:
        return [TranscriptSegment(speaker=Speaker.REP, start=0.0, end=1.0, text="hello")]


class FakeExtractor(ExtractionProvider):
    def extract(self, transcript: list[TranscriptSegment]) -> ExtractionResult:
        return ExtractionResult(
            summary="test summary",
            next_steps=[NextStep(description="call back", owner=Speaker.REP, confidence=0.9)],
            objections=[],
        )


class FailingASR(ASRProvider):
    def transcribe(self, audio_path: Path, dual_channel: bool) -> list[TranscriptSegment]:
        raise RuntimeError("boom")


def _new_record() -> CallRecord:
    return CallRecord(
        id="test-id",
        filename="call.wav",
        dual_channel=False,
        created_at=datetime.now(timezone.utc),
        status="processing",
    )


def test_process_call_succeeds():
    record = process_call(_new_record(), Path("unused.wav"), FakeASR(), FakeExtractor())

    assert record.status == "done"
    assert record.transcript[0].text == "hello"
    assert record.extraction.summary == "test summary"
    assert record.extraction.next_steps[0].owner == Speaker.REP


def test_process_call_records_failure_instead_of_raising():
    record = process_call(_new_record(), Path("unused.wav"), FailingASR(), FakeExtractor())

    assert record.status == "failed"
    assert "boom" in record.error
