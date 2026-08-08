import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile

from app import storage
from app.asr.faster_whisper_provider import FasterWhisperProvider
from app.audio.channel_split import is_dual_channel
from app.extraction.gemini_extractor import GeminiExtractor
from app.pipeline import process_call
from app.schemas import CallRecord, ReviewFeedback

router = APIRouter(prefix="/api/calls", tags=["calls"])

_asr = FasterWhisperProvider()


def _run_pipeline(call_id: str) -> None:
    record = storage.load(call_id)
    if record is None:
        return
    audio_path = storage.audio_path_for(record.id, record.filename)
    try:
        extractor = GeminiExtractor()
    except RuntimeError as exc:
        record.status = "failed"
        record.error = str(exc)
        storage.save(record)
        return

    record = process_call(record, audio_path, _asr, extractor)
    storage.save(record)


@router.post("", status_code=202)
async def upload_call(file: UploadFile, background_tasks: BackgroundTasks) -> CallRecord:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")

    call_id = str(uuid.uuid4())
    audio_path = storage.audio_path_for(call_id, file.filename)
    contents = await file.read()
    audio_path.write_bytes(contents)

    try:
        dual_channel = is_dual_channel(audio_path)
    except Exception as exc:  # noqa: BLE001 — unreadable/corrupt upload
        raise HTTPException(status_code=400, detail=f"Could not read audio file: {exc}") from exc

    record = CallRecord(
        id=call_id,
        filename=file.filename,
        dual_channel=dual_channel,
        created_at=datetime.now(timezone.utc),
        status="processing",
    )
    storage.save(record)
    background_tasks.add_task(_run_pipeline, call_id)
    return record


@router.get("")
async def list_calls() -> list[CallRecord]:
    return storage.list_all()


@router.get("/{call_id}")
async def get_call(call_id: str) -> CallRecord:
    record = storage.load(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return record


@router.post("/{call_id}/feedback")
async def submit_feedback(call_id: str, feedback: ReviewFeedback) -> CallRecord:
    """Manager confirm/reject on an extracted item — the raw signal for the A1
    extraction-precision metric (PRD section 6)."""
    record = storage.load(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Call not found")
    record.feedback = [f for f in record.feedback if not (f.item_type == feedback.item_type and f.item_index == feedback.item_index)]
    record.feedback.append(feedback)
    storage.save(record)
    return record
