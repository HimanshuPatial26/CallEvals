"""Filesystem-backed storage for Team and Agent (ROADMAP.md Phase A) — same
no-database pattern as storage.py, applied to the roster instead of calls.
The roster for a 100-agent org is small enough to hold entirely in memory;
Phase D (Postgres) is where storage actually needs to scale, not here.
"""

import json
from pathlib import Path

from app.config import settings
from app.schemas import Agent, Team

_TEAMS_DIR = settings.data_dir / "teams"
_AGENTS_DIR = settings.data_dir / "agents"
_TEAMS_DIR.mkdir(parents=True, exist_ok=True)
_AGENTS_DIR.mkdir(parents=True, exist_ok=True)


def save_team(team: Team) -> None:
    (_TEAMS_DIR / f"{team.id}.json").write_text(team.model_dump_json(indent=2))


def load_team(team_id: str) -> Team | None:
    path = _TEAMS_DIR / f"{team_id}.json"
    if not path.exists():
        return None
    return Team.model_validate(json.loads(path.read_text()))


def list_teams() -> list[Team]:
    teams = [Team.model_validate(json.loads(p.read_text())) for p in _TEAMS_DIR.glob("*.json")]
    return sorted(teams, key=lambda t: t.name)


def save_agent(agent: Agent) -> None:
    (_AGENTS_DIR / f"{agent.id}.json").write_text(agent.model_dump_json(indent=2))


def load_agent(agent_id: str) -> Agent | None:
    path = _AGENTS_DIR / f"{agent_id}.json"
    if not path.exists():
        return None
    return Agent.model_validate(json.loads(path.read_text()))


def list_agents() -> list[Agent]:
    agents = [Agent.model_validate(json.loads(p.read_text())) for p in _AGENTS_DIR.glob("*.json")]
    return sorted(agents, key=lambda a: a.name)
