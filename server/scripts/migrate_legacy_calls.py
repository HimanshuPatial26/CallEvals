"""One-time migration: CallRecord JSON files saved before ROADMAP.md Phase A
(agent_name + call-level CallOutcome) get rewritten to the current schema
(agent_id + lead_id, with outcome moved onto a Lead).

This was assumed unnecessary when Phase A shipped — server/data/calls/ was
empty in the dev sandbox at the time — but that assumption didn't hold in
every environment: a real deployment with real historical calls hit
`pydantic.ValidationError: agent_id / lead_id Field required` on every
`GET /api/calls`, because storage.list_all() tried to validate old-shape
records against the new CallRecord model. This is ROADMAP.md's A6, done
for real once it turned out to be needed.

Backfills rather than discards:
- `agent_name` -> a real Agent record, deduped by name (so the same
  legacy name across multiple old calls maps to one Agent, not one per
  call), unassigned to a team since the old data has no team concept.
- Each legacy call gets its own new Lead — there's no way to know which
  historical calls were about the same prospect, so one-call-one-lead is
  the honest default rather than guessing. The old call-level
  `outcome.stage` / `deal_size_aed`, if present, is carried onto that
  Lead's stage (with a stage_history entry) rather than dropped.

Idempotent: records that already have agent_id + lead_id are left alone,
so running this twice (or after every future upload) is harmless.

Usage:
    cd server && python -m scripts.migrate_legacy_calls
"""

import json
import uuid
from datetime import datetime, timezone

from app import lead_storage, roster_storage
from app.config import settings
from app.schemas import Agent, FunnelStage, Lead, LeadStageEvent

_RECORDS_DIR = settings.data_dir / "calls"
_NAMESPACE = uuid.UUID("6f6b6e6a-1111-4a00-8a00-63616c6c6576")  # distinct from seed_demo_roster's namespace


def _agent_id_for_legacy_name(name: str, agents_by_name: dict[str, Agent]) -> str:
    existing = agents_by_name.get(name)
    if existing:
        return existing.id
    agent = Agent(id=str(uuid.uuid5(_NAMESPACE, f"legacy-agent:{name}")), name=name, team_id=None, is_manager=False, active=True)
    roster_storage.save_agent(agent)
    agents_by_name[name] = agent
    return agent.id


def _create_legacy_lead(call_stem: str, agent_id: str, old_outcome: dict) -> str:
    lead_id = str(uuid.uuid5(_NAMESPACE, f"legacy-lead:{call_stem}"))
    stage = FunnelStage(old_outcome.get("stage", "untagged"))
    deal_size = old_outcome.get("deal_size_aed")
    now = datetime.now(timezone.utc)
    lead = Lead(
        id=lead_id,
        display_name=f"Legacy call {call_stem[:8]}",
        assigned_agent_id=agent_id,
        stage=stage,
        deal_size_aed=deal_size,
        stage_history=[LeadStageEvent(stage=stage, changed_at=now, changed_by="migration")] if stage != FunnelStage.UNTAGGED else [],
        created_at=now,
    )
    lead_storage.save(lead)
    return lead_id


def migrate() -> None:
    agents_by_name = {a.name: a for a in roster_storage.list_agents()}
    migrated = 0
    already_current = 0
    failed = 0

    for path in sorted(_RECORDS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        if "agent_id" in data and "lead_id" in data:
            already_current += 1
            continue

        try:
            agent_name = data.pop("agent_name", None) or "Unassigned"
            old_outcome = data.pop("outcome", None) or {}

            agent_id = _agent_id_for_legacy_name(agent_name, agents_by_name)
            lead_id = _create_legacy_lead(path.stem, agent_id, old_outcome)

            data["agent_id"] = agent_id
            data["lead_id"] = lead_id
            path.write_text(json.dumps(data, indent=2))
            migrated += 1
        except Exception as exc:  # noqa: BLE001 — report and keep going, don't abort the whole batch
            print(f"  FAILED to migrate {path.name}: {exc}")
            failed += 1

    print(f"Migrated {migrated} legacy call(s), {already_current} already current, {failed} failed.")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    migrate()
