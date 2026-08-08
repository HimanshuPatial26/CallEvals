from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_get_lead():
    response = client.post("/api/leads", json={"display_name": "Ahmed - 2BR Marina", "phone": "+971500000000"})
    assert response.status_code == 201
    lead = response.json()
    assert lead["stage"] == "untagged"

    detail = client.get(f"/api/leads/{lead['id']}").json()
    assert detail["display_name"] == "Ahmed - 2BR Marina"
    assert detail["calls"] == []


def test_create_lead_rejects_empty_display_name():
    response = client.post("/api/leads", json={"display_name": "   "})
    assert response.status_code == 400


def test_create_lead_rejects_unknown_assigned_agent():
    response = client.post("/api/leads", json={"display_name": "Some Lead", "assigned_agent_id": "no-such-agent"})
    assert response.status_code == 400


def test_get_missing_lead_returns_404():
    response = client.get("/api/leads/no-such-lead")
    assert response.status_code == 404


def test_set_stage_appends_history():
    lead = client.post("/api/leads", json={"display_name": "Stage Test Lead"}).json()

    response = client.post(f"/api/leads/{lead['id']}/stage", json={"stage": "qualified"})
    assert response.status_code == 200
    assert response.json()["stage"] == "qualified"

    response = client.post(f"/api/leads/{lead['id']}/stage", json={"stage": "won", "deal_size_aed": 750000})
    body = response.json()
    assert body["stage"] == "won"
    assert body["deal_size_aed"] == 750000
    assert [e["stage"] for e in body["stage_history"]] == ["qualified", "won"]


def test_list_leads_filters_by_stage():
    won_lead = client.post("/api/leads", json={"display_name": "Filter Won Lead"}).json()
    client.post(f"/api/leads/{won_lead['id']}/stage", json={"stage": "won"})
    client.post("/api/leads", json={"display_name": "Filter Untagged Lead"})

    won_only = client.get("/api/leads", params={"stage": "won"}).json()
    assert all(lead["stage"] == "won" for lead in won_only)
    assert any(lead["id"] == won_lead["id"] for lead in won_only)


def test_list_leads_search_by_name():
    client.post("/api/leads", json={"display_name": "Unique Searchable Name XYZ"})
    results = client.get("/api/leads", params={"q": "searchable name xyz"}).json()
    assert len(results) == 1
    assert results[0]["display_name"] == "Unique Searchable Name XYZ"
