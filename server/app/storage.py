"""Filesystem-backed storage for Phase 0. No database — the PRD's own scope cut
(section 8: no vector DB at MVP) extends here too; a handful of design partners in
Phase 1 don't need Postgres yet, and adding it now would be the same kind of stack
decoration the PRD calls out for the vector DB.
"""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.config import settings
from app.schemas import CallRecord

logger = logging.getLogger(__name__)

_RECORDS_DIR = settings.data_dir / "calls"
_AUDIO_DIR = settings.data_dir / "audio"
_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def audio_path_for(call_id: str, filename: str) -> Path:
    suffix = Path(filename).suffix or ".wav"
    return _AUDIO_DIR / f"{call_id}{suffix}"


def save(record: CallRecord) -> None:
    path = _RECORDS_DIR / f"{record.id}.json"
    path.write_text(record.model_dump_json(indent=2))


def load(call_id: str) -> CallRecord | None:
    path = _RECORDS_DIR / f"{call_id}.json"
    if not path.exists():
        return None
    return CallRecord.model_validate(json.loads(path.read_text()))


def list_all() -> list[CallRecord]:
    """Skips (rather than crashes on) a file that fails to parse or validate
    — one legacy-schema or corrupt record shouldn't take down the whole call
    list for everyone else. This is a real failure mode, not hypothetical:
    calls saved before the agent_id/lead_id schema change (pre ROADMAP.md
    Phase A) fail validation here. Run `python -m scripts.migrate_legacy_calls`
    to fix them forward instead of leaving them silently excluded."""
    records = []
    for path in _RECORDS_DIR.glob("*.json"):
        try:
            records.append(CallRecord.model_validate(json.loads(path.read_text())))
        except (ValidationError, json.JSONDecodeError) as exc:
            logger.warning(
                "Skipping unreadable call record %s (%s) — run "
                "`python -m scripts.migrate_legacy_calls` if this is a pre-Phase-A record.",
                path.name,
                exc,
            )
    return sorted(records, key=lambda r: r.created_at, reverse=True)
