import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_list_teams():
    response = client.post("/api/teams", json={"name": "Downtown"})
    assert response.status_code == 201
    team_id = response.json()["id"]

    listed = client.get("/api/teams").json()
    assert any(t["id"] == team_id and t["name"] == "Downtown" for t in listed)


def test_create_team_rejects_unknown_manager():
    response = client.post("/api/teams", json={"name": "Marina", "manager_agent_id": "no-such-agent"})
    assert response.status_code == 400


def test_create_and_list_agents():
    response = client.post("/api/agents", json={"name": "Fatima Noor"})
    assert response.status_code == 201
    agent_id = response.json()["id"]

    listed = client.get("/api/agents").json()
    entry = next(a for a in listed if a["id"] == agent_id)
    assert entry["name"] == "Fatima Noor"
    assert entry["calls_analyzed"] == 0
    assert entry["team_name"] is None


def test_create_agent_rejects_unknown_team():
    response = client.post("/api/agents", json={"name": "Ghost", "team_id": "no-such-team"})
    assert response.status_code == 400


def test_agent_roster_entry_resolves_team_name():
    team = client.post("/api/teams", json={"name": "Resolvable Team"}).json()
    agent = client.post("/api/agents", json={"name": "Team Member", "team_id": team["id"]}).json()

    listed = client.get("/api/agents").json()
    entry = next(a for a in listed if a["id"] == agent["id"])
    assert entry["team_name"] == "Resolvable Team"


def test_patch_agent_updates_team_assignment():
    team = client.post("/api/teams", json={"name": "Patch Target Team"}).json()
    agent = client.post("/api/agents", json={"name": "Patchable"}).json()

    response = client.patch(f"/api/agents/{agent['id']}", json={"team_id": team["id"], "active": False})
    assert response.status_code == 200
    body = response.json()
    assert body["team_id"] == team["id"]
    assert body["active"] is False


def test_patch_missing_agent_returns_404():
    response = client.patch("/api/agents/no-such-agent", json={"active": False})
    assert response.status_code == 404


def test_import_agents_from_json_auto_creates_teams():
    payload = [
        {"name": "Imported One", "team_name": "Imported Team A", "is_manager": True},
        {"name": "Imported Two", "team_name": "Imported Team A"},
    ]
    import json as json_module

    response = client.post(
        "/api/agents/import",
        files={"file": ("agents.json", io.BytesIO(json_module.dumps(payload).encode()), "application/json")},
    )
    assert response.status_code == 200
    created = response.json()
    assert len(created) == 2
    assert created[0]["team_id"] == created[1]["team_id"]  # both landed on the same auto-created team
    assert created[0]["is_manager"] is True

    teams = client.get("/api/teams").json()
    assert any(t["name"] == "Imported Team A" for t in teams)


def test_import_agents_from_csv():
    csv_content = "name,team_name,is_manager\nCSV Agent One,CSV Team,false\nCSV Agent Two,CSV Team,true\n"
    response = client.post(
        "/api/agents/import",
        files={"file": ("agents.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert response.status_code == 200
    created = response.json()
    assert len(created) == 2
    assert created[1]["is_manager"] is True


def test_import_rejects_unsupported_file_type():
    response = client.post(
        "/api/agents/import",
        files={"file": ("agents.txt", io.BytesIO(b"not a real import"), "text/plain")},
    )
    assert response.status_code == 400
