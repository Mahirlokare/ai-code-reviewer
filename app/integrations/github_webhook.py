"""GitHub webhook signature verification using standard-library HMAC."""
from __future__ import annotations
import hashlib
import hmac


def verify_github_signature(payload: bytes, signature_header: str | None, secret: str | None) -> bool:
    """Return True only for a valid sha256 signature and configured secret."""
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
