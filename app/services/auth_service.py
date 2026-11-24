"""Cryptographically secure password hashing and token management."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.core.config import settings


def hash_password(password: str) -> str:
    """Generate salted PBKDF2-HMAC-SHA256 hash."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt and key using timing-safe comparison."""
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(expected_key.hex(), key_hex)
    except Exception:
        return False


def create_access_token(user_id: str, username: str, email: str, expires_in_seconds: int = 86400 * 30) -> str:
    """Generate a tamper-proof signed session token."""
    payload = {
        "uid": user_id,
        "usr": username,
        "eml": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in_seconds,
    }
    raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(raw_json).decode("utf-8").rstrip("=")
    
    secret = settings.jwt_secret.encode("utf-8")
    signature = hmac.new(secret, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{signature}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Verify token signature and return payload if valid and unexpired."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 2:
            return None
        b64_payload, signature = parts
        
        secret = settings.jwt_secret.encode("utf-8")
        expected_sig = hmac.new(secret, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            return None
        
        # Add padding for base64 decode
        padded = b64_payload + "=" * (-len(b64_payload) % 4)
        raw_json = base64.urlsafe_b64decode(padded).decode("utf-8")
        payload = json.loads(raw_json)
        
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
