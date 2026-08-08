from app import roster_storage
from app.schemas import Agent, Team


def test_team_round_trips():
    team = Team(id="team-1", name="Alpha")
    roster_storage.save_team(team)
    assert roster_storage.load_team("team-1") == team


def test_load_missing_team_returns_none():
    assert roster_storage.load_team("no-such-team") is None


def test_list_teams_sorted_by_name():
    roster_storage.save_team(Team(id="t2", name="Zeta"))
    roster_storage.save_team(Team(id="t1", name="Alpha"))
    names = [t.name for t in roster_storage.list_teams() if t.id in ("t1", "t2")]
    assert names == ["Alpha", "Zeta"]


def test_agent_round_trips():
    agent = Agent(id="agent-1", name="Rahul Sharma", team_id="team-1", is_manager=False)
    roster_storage.save_agent(agent)
    assert roster_storage.load_agent("agent-1") == agent


def test_load_missing_agent_returns_none():
    assert roster_storage.load_agent("no-such-agent") is None


def test_list_agents_sorted_by_name():
    roster_storage.save_agent(Agent(id="a2", name="Zainab"))
    roster_storage.save_agent(Agent(id="a1", name="Ahmed"))
    names = [a.name for a in roster_storage.list_agents() if a.id in ("a1", "a2")]
    assert names == ["Ahmed", "Zainab"]
