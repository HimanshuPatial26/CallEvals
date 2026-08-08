"""Orchestrates F1 -> F2/F3/F4 (+ behavior insights): audio in, transcript,
extraction, and call insights out.

Split out from the FastAPI route so the Phase 0 precision eval (eval/run_precision_eval.py)
can drive extraction directly against scripted transcripts without going through
HTTP or touching audio at all.
"""

from pathlib import Path

from app.asr.base import ASRProvider
from app.compliance import compute_compliance
from app.extraction.base import ExtractionProvider
from app.insights import compute_call_insights
from app.schemas import CallRecord

COMPLIANCE_MAX_POINTS = 5.0  # doc section 18 — Compliance/Process Adherence weight out of 100


def process_call(record: CallRecord, audio_path: Path, asr: ASRProvider, extractor: ExtractionProvider) -> CallRecord:
    try:
        record.transcript = asr.transcribe(audio_path, dual_channel=record.dual_channel)
        record.extraction = extractor.extract(record.transcript)
        record.insights = compute_call_insights(record.transcript)
        record.compliance = compute_compliance(record.transcript)
        record.overall_score = _compute_overall_score(record)
        record.status = "done"
    except Exception as exc:  # noqa: BLE001 — surfaced to the review UI, not swallowed
        record.status = "failed"
        record.error = str(exc)
    return record


def _compute_overall_score(record: CallRecord) -> float | None:
    """Sum of the 7 LLM-scored rubric dimensions plus the compliance-derived
    score. None if the extractor didn't produce a score_breakdown (e.g. a
    fake/stub extractor in tests) rather than a misleading 0."""
    breakdown = record.extraction.score_breakdown if record.extraction else None
    if breakdown is None or record.compliance is None:
        return None

    dimension_total = sum(
        dim.score
        for dim in (
            breakdown.opening_rapport,
            breakdown.discovery_qualification,
            breakdown.active_listening,
            breakdown.pitch_value_prop,
            breakdown.objection_handling,
            breakdown.communication_professionalism,
            breakdown.closing_next_steps,
        )
    )
    compliance_score = (record.compliance.adherence_pct / 100.0) * COMPLIANCE_MAX_POINTS
    return dimension_total + compliance_score
