"""Synthetic demo roster — 10 teams x 10 agents (1 manager each) = ~100
agents, matching the target scenario in docs/ROADMAP.md ("~100 sales
agents, 10 teams of ~10, 10 managers"). Demo/testing data ONLY.

Every name here is a randomly-combined first/last name, not a real person —
the pools reflect the PRD's ICP (PRD section 3: Dubai/Abu Dhabi real estate
brokerages, whose sales floors are genuinely this mixed) purely so the demo
doesn't look like a placeholder "Agent 1, Agent 2" list, not because any
of it refers to anyone real. Team names are Dubai/Abu Dhabi neighborhoods,
also chosen only for flavor.

Idempotent: every Team/Agent ID is a uuid5 derived from its name, so
re-running this script updates the same records instead of creating
duplicates — safe to run again after tweaking the pools.

Usage:
    cd server && python -m scripts.seed_demo_roster
"""

import random
import uuid

from app import roster_storage
from app.schemas import Agent, Team

_NAMESPACE = uuid.UUID("6f6b6e6a-0000-4a00-8a00-63616c6c6576")  # arbitrary, fixed — "callev"-ish

TEAM_NAMES = [
    "Downtown Team",
    "Marina Team",
    "Palm Jumeirah Team",
    "Business Bay Team",
    "JBR Team",
    "Al Reem Island Team",
    "Corniche Team",
    "Yas Island Team",
    "Dubai Hills Team",
    "Arabian Ranches Team",
]

FIRST_NAMES = [
    # Reflects the actual mix on a Dubai/Abu Dhabi real-estate sales floor
    # (PRD section 3's ICP) — not drawn from or referring to real people.
    "Ahmed", "Mohammed", "Ali", "Omar", "Khalid", "Youssef", "Hassan", "Tariq", "Rashid", "Faisal",
    "Zayed", "Saeed", "Salem", "Nasser", "Fahad",
    "Fatima", "Aisha", "Mariam", "Layla", "Noura", "Salma", "Huda", "Amina", "Reem", "Sara",
    "Dana", "Hind", "Maha", "Rania", "Nadia",
    "James", "Michael", "David", "Daniel", "Robert", "John", "Andrew", "Ryan", "Thomas", "Chris",
    "Sarah", "Emma", "Jennifer", "Jessica", "Amanda", "Michelle", "Laura", "Emily", "Rachel", "Olivia",
    "Raj", "Arjun", "Vikram", "Rohan", "Sanjay", "Amit", "Deepak",
    "Priya", "Anjali", "Divya", "Neha", "Pooja",
    "Miguel", "Carlos", "Jose", "Antonio",
    "Maria", "Carmen", "Isabella",
]

LAST_NAMES = [
    "Al Mansoori", "Al Suwaidi", "Al Falasi", "Al Marri", "Al Shamsi",
    "Khan", "Sharma", "Patel", "Reddy", "Nair", "Menon",
    "Fernandez", "Santos", "Cruz", "D'Souza",
    "Johnson", "Smith", "Williams", "Brown", "Taylor", "Anderson", "Wilson", "Clark",
    "Rahman", "Hussain", "Malik",
]

AGENTS_PER_TEAM = 10


def _deterministic_id(kind: str, name: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, f"{kind}:{name}"))


def generate_names(count: int, seed: int = 42) -> list[str]:
    rng = random.Random(seed)
    pairs = [(first, last) for first in FIRST_NAMES for last in LAST_NAMES]
    rng.shuffle(pairs)
    names = [f"{first} {last}" for first, last in pairs[:count]]
    if len(names) < count:
        raise ValueError(f"name pool too small: need {count} unique combinations, have {len(pairs)}")
    return names


def seed() -> None:
    names = generate_names(len(TEAM_NAMES) * AGENTS_PER_TEAM)
    name_iter = iter(names)

    teams_created = 0
    agents_created = 0

    for team_name in TEAM_NAMES:
        team_id = _deterministic_id("team", team_name)
        team_agent_names = [next(name_iter) for _ in range(AGENTS_PER_TEAM)]
        manager_name = team_agent_names[0]
        manager_id = _deterministic_id("agent", f"{team_name}:{manager_name}")

        roster_storage.save_team(Team(id=team_id, name=team_name, manager_agent_id=manager_id))
        teams_created += 1

        for i, agent_name in enumerate(team_agent_names):
            agent_id = _deterministic_id("agent", f"{team_name}:{agent_name}")
            roster_storage.save_agent(
                Agent(id=agent_id, name=agent_name, team_id=team_id, is_manager=(i == 0), active=True)
            )
            agents_created += 1

    print(f"Seeded {teams_created} teams and {agents_created} agents (demo data only).")


if __name__ == "__main__":
    seed()
