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


def test_set_stage_records_lost_reason():
    lead = client.post("/api/leads", json={"display_name": "Lost Reason Test Lead"}).json()

    response = client.post(f"/api/leads/{lead['id']}/stage", json={"stage": "lost", "lost_reason": "price"})
    assert response.status_code == 200
    assert response.json()["lost_reason"] == "price"


def test_reassign_updates_agent_and_appends_history():
    agent = client.post("/api/agents", json={"name": "Reassign Target Agent"}).json()
    lead = client.post("/api/leads", json={"display_name": "Reassign Test Lead"}).json()

    response = client.post(f"/api/leads/{lead['id']}/reassign", json={"assigned_agent_id": agent["id"], "changed_by": "manager-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["assigned_agent_id"] == agent["id"]
    assert len(body["assignment_history"]) == 1
    assert body["assignment_history"][0]["assigned_agent_id"] == agent["id"]


def test_reassign_rejects_unknown_agent():
    lead = client.post("/api/leads", json={"display_name": "Reassign Reject Test Lead"}).json()
    response = client.post(f"/api/leads/{lead['id']}/reassign", json={"assigned_agent_id": "no-such-agent"})
    assert response.status_code == 400


def test_reassign_missing_lead_returns_404():
    response = client.post("/api/leads/no-such-lead/reassign", json={"assigned_agent_id": None})
    assert response.status_code == 404


def test_update_lead_edits_only_provided_fields():
    lead = client.post("/api/leads", json={"display_name": "Update Test Lead", "phone": "+971500000001"}).json()

    response = client.patch(f"/api/leads/{lead['id']}", json={"source": "website"})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "website"
    assert body["display_name"] == "Update Test Lead"  # untouched
    assert body["phone"] == "+971500000001"  # untouched


def test_update_lead_rejects_blank_display_name():
    lead = client.post("/api/leads", json={"display_name": "Blank Name Test Lead"}).json()
    response = client.patch(f"/api/leads/{lead['id']}", json={"display_name": "   "})
    assert response.status_code == 400


def test_update_missing_lead_returns_404():
    response = client.patch("/api/leads/no-such-lead", json={"source": "website"})
    assert response.status_code == 404
