"""Orchestrates F1 -> F2/F3/F4: audio in, transcript + extraction out.

Split out from the FastAPI route so the Phase 0 precision eval (eval/run_precision_eval.py)
can drive extraction directly against scripted transcripts without going through
HTTP or touching audio at all.
"""

from pathlib import Path

from app.asr.base import ASRProvider
from app.extraction.base import ExtractionProvider
from app.schemas import CallRecord


def process_call(record: CallRecord, audio_path: Path, asr: ASRProvider, extractor: ExtractionProvider) -> CallRecord:
    try:
        record.transcript = asr.transcribe(audio_path, dual_channel=record.dual_channel)
        record.extraction = extractor.extract(record.transcript)
        record.status = "done"
    except Exception as exc:  # noqa: BLE001 — surfaced to the review UI, not swallowed
        record.status = "failed"
        record.error = str(exc)
    return record
