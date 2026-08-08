from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_org_performance_with_no_data_returns_empty_report():
    response = client.get("/api/organization/performance", params={"start": "2026-08-01", "end": "2026-08-31"})
    assert response.status_code == 200
    body = response.json()
    assert "calls_analyzed" in body
    assert "team_leaderboard" in body
    assert "team_benchmark" not in body  # org level has no peer to benchmark against


def test_org_performance_rejects_inverted_date_range():
    response = client.get("/api/organization/performance", params={"start": "2026-08-31", "end": "2026-08-01"})
    assert response.status_code == 400
