from datetime import datetime, timezone
from pathlib import Path

from app.asr.base import ASRProvider
from app.extraction.base import ExtractionProvider
from app.pipeline import process_call
from app.schemas import (
    CallRecord,
    DimensionScore,
    ExtractionResult,
    NextStep,
    ScoreBreakdown,
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


def _dim(score: float, max_score: float) -> DimensionScore:
    return DimensionScore(score=score, max_score=max_score, evidence="test evidence")


class FakeExtractorWithScores(ExtractionProvider):
    def extract(self, transcript: list[TranscriptSegment]) -> ExtractionResult:
        return ExtractionResult(
            summary="test summary",
            next_steps=[],
            objections=[],
            score_breakdown=ScoreBreakdown(
                opening_rapport=_dim(8, 10),
                discovery_qualification=_dim(15, 20),
                active_listening=_dim(7, 10),
                pitch_value_prop=_dim(12, 15),
                objection_handling=_dim(10, 15),
                communication_professionalism=_dim(9, 10),
                closing_next_steps=_dim(10, 15),
            ),
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
    assert record.insights is not None
    assert record.insights.rep_talk_time_ratio == 1.0
    assert record.compliance is not None


def test_process_call_records_failure_instead_of_raising():
    record = process_call(_new_record(), Path("unused.wav"), FailingASR(), FakeExtractor())

    assert record.status == "failed"
    assert "boom" in record.error
    assert record.insights is None


def test_overall_score_is_none_without_a_score_breakdown():
    record = process_call(_new_record(), Path("unused.wav"), FakeASR(), FakeExtractor())
    assert record.extraction.score_breakdown is None
    assert record.overall_score is None


def test_overall_score_sums_dimensions_plus_compliance():
    record = process_call(_new_record(), Path("unused.wav"), FakeASR(), FakeExtractorWithScores())

    dimension_total = 8 + 15 + 7 + 12 + 10 + 9 + 10  # = 71
    expected_compliance_points = record.compliance.adherence_pct / 100.0 * 5.0
    assert record.overall_score == dimension_total + expected_compliance_points
