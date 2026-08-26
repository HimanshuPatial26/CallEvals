"""Filesystem-backed storage for Phase 0. No database — the PRD's own scope cut
(section 8: no vector DB at MVP) extends here too; a handful of design partners in
Phase 1 don't need Postgres yet, and adding it now would be the same kind of stack
decoration the PRD calls out for the vector DB.
"""

import json
import logging
import os
from pathlib import Path

from pydantic import BaseModel, ValidationError

from app.config import settings
from app.schemas import Agent, CallRecord, Lead, RubricSettings

logger = logging.getLogger(__name__)

_RECORDS_DIR = settings.data_dir / "calls"
_AUDIO_DIR = settings.data_dir / "audio"
_AGENTS_DIR = settings.data_dir / "agents"
_LEADS_DIR = settings.data_dir / "leads"
_SETTINGS_PATH = settings.data_dir / "settings.json"
_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
_LEADS_DIR.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, model: BaseModel) -> None:
    """Write via a temp file + atomic rename, so a process killed mid-write
    (Ctrl+C, crash, OOM) leaves the old file intact instead of a truncated,
    unparseable one — os.replace is atomic on both POSIX and Windows."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(model.model_dump_json(indent=2))
    os.replace(tmp_path, path)


def _read_json(path: Path, model_cls):
    """Returns None (and logs) rather than raising for a file that doesn't exist,
    is empty/truncated, or fails schema validation — a single damaged record
    should surface as "not found" for that record, not a 500 for every caller."""
    if not path.exists():
        return None
    try:
        return model_cls.model_validate(json.loads(path.read_text()))
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Skipping unreadable %s: %s", path, exc)
        return None


def audio_path_for(call_id: str, filename: str) -> Path:
    suffix = Path(filename).suffix or ".wav"
    return _AUDIO_DIR / f"{call_id}{suffix}"


def save(record: CallRecord) -> None:
    _write_json(_RECORDS_DIR / f"{record.id}.json", record)


def load(call_id: str) -> CallRecord | None:
    return _read_json(_RECORDS_DIR / f"{call_id}.json", CallRecord)


def list_all() -> list[CallRecord]:
    records = [r for p in _RECORDS_DIR.glob("*.json") if (r := _read_json(p, CallRecord)) is not None]
    return sorted(records, key=lambda r: r.created_at, reverse=True)


def save_agent(agent: Agent) -> None:
    _write_json(_AGENTS_DIR / f"{agent.id}.json", agent)


def load_agent(agent_id: str) -> Agent | None:
    return _read_json(_AGENTS_DIR / f"{agent_id}.json", Agent)


def find_agent_by_name(name: str) -> Agent | None:
    return next((a for a in list_agents() if a.name.strip().lower() == name.strip().lower()), None)


def list_agents() -> list[Agent]:
    agents = [a for p in _AGENTS_DIR.glob("*.json") if (a := _read_json(p, Agent)) is not None]
    return sorted(agents, key=lambda a: a.name)


def save_lead(lead: Lead) -> None:
    _write_json(_LEADS_DIR / f"{lead.id}.json", lead)


def load_lead(lead_id: str) -> Lead | None:
    return _read_json(_LEADS_DIR / f"{lead_id}.json", Lead)


def find_lead_by_phone(phone: str) -> Lead | None:
    return next((l for l in list_leads() if l.phone.strip() == phone.strip()), None)


def list_leads() -> list[Lead]:
    leads = [l for p in _LEADS_DIR.glob("*.json") if (l := _read_json(p, Lead)) is not None]
    return sorted(leads, key=lambda l: l.created_at, reverse=True)


def load_settings() -> RubricSettings:
    return _read_json(_SETTINGS_PATH, RubricSettings) or RubricSettings()


def save_settings(rubric: RubricSettings) -> None:
    _write_json(_SETTINGS_PATH, rubric)
