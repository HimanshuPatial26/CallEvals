import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app import storage
from app.asr.factory import get_asr_provider
from app.audio.channel_split import is_dual_channel
from app.extraction.gemini_extractor import GeminiExtractor
from app.pipeline import process_call
from app.schemas import Agent, CallRecord, Lead, ReviewFeedback

router = APIRouter(prefix="/api/calls", tags=["calls"])


def _run_pipeline(call_id: str) -> None:
    record = storage.load(call_id)
    if record is None:
        return
    audio_path = storage.audio_path_for(record.id, record.filename)
    try:
        asr = get_asr_provider()
        extractor = GeminiExtractor()
    except RuntimeError as exc:
        record.status = "failed"
        record.error = str(exc)
        storage.save(record)
        return

    record = process_call(record, audio_path, asr, extractor)
    storage.save(record)


def _resolve_agent(agent_name: str | None) -> str | None:
    if not agent_name or not agent_name.strip():
        return None
    existing = storage.find_agent_by_name(agent_name)
    if existing:
        return existing.id
    agent = Agent(id=str(uuid.uuid4()), name=agent_name.strip())
    storage.save_agent(agent)
    return agent.id


def _resolve_lead(
    lead_phone: str | None, lead_name: str | None, unit: str | None, budget: str | None, source: str | None
) -> str | None:
    if not lead_phone or not lead_phone.strip():
        return None
    existing = storage.find_lead_by_phone(lead_phone)
    if existing:
        return existing.id
    lead = Lead(
        id=str(uuid.uuid4()),
        name=(lead_name or lead_phone).strip(),
        phone=lead_phone.strip(),
        unit=unit,
        budget=budget,
        source=source,
        created_at=datetime.now(timezone.utc),
    )
    storage.save_lead(lead)
    return lead.id


@router.post("", status_code=202)
async def upload_call(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    agent_name: str | None = Form(None),
    lead_phone: str | None = Form(None),
    lead_name: str | None = Form(None),
    lead_unit: str | None = Form(None),
    lead_budget: str | None = Form(None),
    lead_source: str | None = Form(None),
) -> CallRecord:
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
        agent_id=_resolve_agent(agent_name),
        lead_id=_resolve_lead(lead_phone, lead_name, lead_unit, lead_budget, lead_source),
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
    if record.first_viewed_at is None:
        record.first_viewed_at = datetime.now(timezone.utc)
        storage.save(record)
    return record


@router.get("/{call_id}/audio")
async def get_call_audio(call_id: str) -> FileResponse:
    record = storage.load(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Call not found")
    audio_path = storage.audio_path_for(call_id, record.filename)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path, filename=record.filename)


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
