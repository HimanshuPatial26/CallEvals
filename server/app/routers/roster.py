"""Team/Agent roster CRUD (ROADMAP.md Phase A). No auth yet (Phase E) — every
route here is unrestricted, matching the rest of this Phase 0 build.
"""

import csv
import io
import json
import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app import roster_storage, storage
from app.schemas import Agent, Team

router = APIRouter(tags=["roster"])


class TeamCreate(BaseModel):
    name: str
    manager_agent_id: str | None = None


class AgentCreate(BaseModel):
    name: str
    team_id: str | None = None
    is_manager: bool = False


class AgentUpdate(BaseModel):
    name: str | None = None
    team_id: str | None = None
    is_manager: bool | None = None
    active: bool | None = None


@router.post("/api/teams", status_code=201)
async def create_team(body: TeamCreate) -> Team:
    if body.manager_agent_id and roster_storage.load_agent(body.manager_agent_id) is None:
        raise HTTPException(status_code=400, detail=f"manager_agent_id {body.manager_agent_id!r} does not exist")
    team = Team(id=str(uuid.uuid4()), name=body.name, manager_agent_id=body.manager_agent_id)
    roster_storage.save_team(team)
    return team


@router.get("/api/teams")
async def list_teams() -> list[Team]:
    return roster_storage.list_teams()


@router.post("/api/agents", status_code=201)
async def create_agent(body: AgentCreate) -> Agent:
    if body.team_id and roster_storage.load_team(body.team_id) is None:
        raise HTTPException(status_code=400, detail=f"team_id {body.team_id!r} does not exist")
    agent = Agent(id=str(uuid.uuid4()), name=body.name, team_id=body.team_id, is_manager=body.is_manager)
    roster_storage.save_agent(agent)
    return agent


@router.get("/api/agents")
async def list_agents() -> list[dict]:
    """The real roster, enriched with a calls_analyzed count for the picker
    UI — resolved here at the API layer rather than stored on Agent, so it's
    never stale."""
    agents = roster_storage.list_agents()
    teams_by_id = {t.id: t for t in roster_storage.list_teams()}
    counts: dict[str, int] = {}
    for record in storage.list_all():
        if record.status == "done":
            counts[record.agent_id] = counts.get(record.agent_id, 0) + 1
    return [
        {
            "id": a.id,
            "name": a.name,
            "team_id": a.team_id,
            "team_name": teams_by_id[a.team_id].name if a.team_id in teams_by_id else None,
            "is_manager": a.is_manager,
            "active": a.active,
            "calls_analyzed": counts.get(a.id, 0),
        }
        for a in agents
    ]


@router.patch("/api/agents/{agent_id}")
async def update_agent(agent_id: str, body: AgentUpdate) -> Agent:
    agent = roster_storage.load_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if body.team_id is not None and roster_storage.load_team(body.team_id) is None:
        raise HTTPException(status_code=400, detail=f"team_id {body.team_id!r} does not exist")
    update_data = body.model_dump(exclude_unset=True)
    updated = agent.model_copy(update=update_data)
    roster_storage.save_agent(updated)
    return updated


def _parse_import_rows(filename: str, contents: bytes) -> list[dict]:
    if filename.lower().endswith(".json"):
        rows = json.loads(contents.decode("utf-8"))
        if not isinstance(rows, list):
            raise HTTPException(status_code=400, detail="JSON import must be a list of {name, team_name, is_manager}")
        return rows
    if filename.lower().endswith(".csv"):
        reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))
        return [
            {
                "name": row.get("name", "").strip(),
                "team_name": (row.get("team_name") or "").strip() or None,
                "is_manager": (row.get("is_manager") or "").strip().lower() in ("1", "true", "yes"),
            }
            for row in reader
        ]
    raise HTTPException(status_code=400, detail="Import file must be .csv or .json")


@router.post("/api/agents/import")
async def import_agents(file: UploadFile) -> list[Agent]:
    """Bulk-create agents from a CSV or JSON file (columns/keys: name,
    team_name, is_manager). Referenced teams are auto-created if they don't
    already exist by name — a one-shot seed for a ~100-agent/10-team org
    shouldn't require creating the 10 teams by hand first. No dedup by name:
    running the same import twice creates duplicate agents."""
    contents = await file.read()
    rows = _parse_import_rows(file.filename or "", contents)

    existing_teams = {t.name: t for t in roster_storage.list_teams()}
    created: list[Agent] = []
    for row in rows:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        team_name = row.get("team_name")
        team_id = None
        if team_name:
            team = existing_teams.get(team_name)
            if team is None:
                team = Team(id=str(uuid.uuid4()), name=team_name)
                roster_storage.save_team(team)
                existing_teams[team_name] = team
            team_id = team.id
        agent = Agent(id=str(uuid.uuid4()), name=name, team_id=team_id, is_manager=bool(row.get("is_manager", False)))
        roster_storage.save_agent(agent)
        created.append(agent)

    return created
