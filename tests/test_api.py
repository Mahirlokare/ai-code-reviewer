"""API smoke tests."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_review_endpoint_returns_structured_result() -> None:
    response = client.post("/api/v1/reviews", json={"diff": "@@ -0,0 +1 @@\n+print('debug')", "language": "python"})
    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert "findings" in payload
    assert payload["engine"] == "heuristic-v0"
