"""Webhook endpoint tests covering missing and valid signatures."""
import hashlib
import hmac
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_webhook_rejects_missing_signature() -> None:
    response = client.post("/api/v1/webhooks/github", content=b'{"zen":"test"}',
                          headers={"X-GitHub-Event": "ping"})
    assert response.status_code == 401


def test_webhook_ping_with_signature(monkeypatch) -> None:
    secret = "unit-test-secret"
    monkeypatch.setattr(settings, "github_webhook_secret", secret)
    payload = b'{"zen":"test"}'
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post("/api/v1/webhooks/github", content=payload,
                           headers={"X-GitHub-Event": "ping", "X-Hub-Signature-256": "sha256=" + digest})
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
