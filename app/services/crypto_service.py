"""Authenticated AES-256-GCM encryption at rest for sensitive database & session data."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from functools import lru_cache

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings

ENC_PREFIX = "enc:v1:"


@lru_cache(maxsize=4)
def _derive_aes_key(master_secret: str) -> bytes:
    """Derive a 256-bit AES key from the configured encryption/JWT secret using HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"reviewpilot-aes256-gcm-v1",
        info=b"sensitive-data-at-rest",
    )
    return hkdf.derive(master_secret.encode("utf-8"))


def _get_master_secret() -> str:
    return settings.encryption_key or settings.jwt_secret


def encrypt_sensitive(plaintext: str | None) -> str | None:
    """Encrypt sensitive string using AES-256-GCM with a random 96-bit nonce."""
    if plaintext is None or plaintext == "":
        return plaintext
    if plaintext.startswith(ENC_PREFIX):
        return plaintext

    key = _derive_aes_key(_get_master_secret())
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), b"reviewpilot-v1")
    token = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{ENC_PREFIX}{token}"


def decrypt_sensitive(value: str | None) -> str | None:
    """Decrypt AES-256-GCM value; gracefully returns legacy plaintext if unencrypted."""
    if value is None or value == "":
        return value
    if not value.startswith(ENC_PREFIX):
        return value

    encoded = value[len(ENC_PREFIX):]
    raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
    if len(raw) < 13:
        raise ValueError("Corrupted encrypted payload.")
    nonce, ciphertext = raw[:12], raw[12:]
    key = _derive_aes_key(_get_master_secret())
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, b"reviewpilot-v1")
    return plaintext.decode("utf-8")


def blind_index(value: str) -> str:
    """Compute keyed HMAC-SHA256 blind index for exact-match lookups on encrypted columns."""
    secret = _get_master_secret().encode("utf-8")
    normalized = value.strip().lower().encode("utf-8")
    return hmac.new(secret, normalized, hashlib.sha256).hexdigest()
