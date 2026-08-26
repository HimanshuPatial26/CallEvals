"""Filesystem-backed storage for Phase 0. No database — the PRD's own scope cut
(section 8: no vector DB at MVP) extends here too; a handful of design partners in
Phase 1 don't need Postgres yet, and adding it now would be the same kind of stack
decoration the PRD calls out for the vector DB.
"""

import json
from pathlib import Path

from app.config import settings
from app.schemas import Agent, CallRecord, Lead, RubricSettings

_RECORDS_DIR = settings.data_dir / "calls"
_AUDIO_DIR = settings.data_dir / "audio"
_AGENTS_DIR = settings.data_dir / "agents"
_LEADS_DIR = settings.data_dir / "leads"
_SETTINGS_PATH = settings.data_dir / "settings.json"
_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
_LEADS_DIR.mkdir(parents=True, exist_ok=True)


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
    records = [CallRecord.model_validate(json.loads(p.read_text())) for p in _RECORDS_DIR.glob("*.json")]
    return sorted(records, key=lambda r: r.created_at, reverse=True)


def save_agent(agent: Agent) -> None:
    (_AGENTS_DIR / f"{agent.id}.json").write_text(agent.model_dump_json(indent=2))


def load_agent(agent_id: str) -> Agent | None:
    path = _AGENTS_DIR / f"{agent_id}.json"
    if not path.exists():
        return None
    return Agent.model_validate(json.loads(path.read_text()))


def find_agent_by_name(name: str) -> Agent | None:
    return next((a for a in list_agents() if a.name.strip().lower() == name.strip().lower()), None)


def list_agents() -> list[Agent]:
    return sorted(
        (Agent.model_validate(json.loads(p.read_text())) for p in _AGENTS_DIR.glob("*.json")),
        key=lambda a: a.name,
    )


def save_lead(lead: Lead) -> None:
    (_LEADS_DIR / f"{lead.id}.json").write_text(lead.model_dump_json(indent=2))


def load_lead(lead_id: str) -> Lead | None:
    path = _LEADS_DIR / f"{lead_id}.json"
    if not path.exists():
        return None
    return Lead.model_validate(json.loads(path.read_text()))


def find_lead_by_phone(phone: str) -> Lead | None:
    return next((l for l in list_leads() if l.phone.strip() == phone.strip()), None)


def list_leads() -> list[Lead]:
    records = [Lead.model_validate(json.loads(p.read_text())) for p in _LEADS_DIR.glob("*.json")]
    return sorted(records, key=lambda l: l.created_at, reverse=True)


def load_settings() -> RubricSettings:
    if not _SETTINGS_PATH.exists():
        return RubricSettings()
    return RubricSettings.model_validate(json.loads(_SETTINGS_PATH.read_text()))


def save_settings(rubric: RubricSettings) -> None:
    _SETTINGS_PATH.write_text(rubric.model_dump_json(indent=2))
