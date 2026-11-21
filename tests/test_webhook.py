"""Webhook signature verification tests."""
import hashlib
import hmac
from app.integrations.github_webhook import verify_github_signature


def test_valid_signature_accepted() -> None:
    body = b'{"action":"opened"}'
    secret = "test-secret"
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_github_signature(body, "sha256=" + digest, secret)


def test_wrong_signature_rejected() -> None:
    assert not verify_github_signature(b"body", "sha256=wrong", "secret")


def test_missing_secret_or_header_rejected() -> None:
    assert not verify_github_signature(b"body", None, "secret")
    assert not verify_github_signature(b"body", "sha256=anything", None)
