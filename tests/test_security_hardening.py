"""Security hardening tests: AES-256-GCM encryption, SSRF, rate limiting, and zero Google Fonts."""
import sqlite3
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core.security import LoginBruteForceGuard, SlidingWindowRateLimiter, validate_github_identifier
from app.schemas.review import Finding, ReviewResponse
from app.services.crypto_service import ENC_PREFIX, blind_index, decrypt_sensitive, encrypt_sensitive
from app.services.email_service import send_signup_confirmation_email
from app.storage.repository import StorageRepository


def test_aes_256_gcm_encryption_and_tamper_detection() -> None:
    secret_text = "Sensitive user email body & token: secret-123"
    encrypted = encrypt_sensitive(secret_text)
    assert encrypted is not None
    assert encrypted.startswith(ENC_PREFIX)
    assert secret_text not in encrypted
    assert decrypt_sensitive(encrypted) == secret_text

    # Legacy plaintext compatibility
    assert decrypt_sensitive("legacy-plain") == "legacy-plain"

    # Tampered ciphertext must fail authentication tag verification
    tampered = encrypted[:-4] + ("AAAA" if encrypted[-4:] != "AAAA" else "BBBB")
    with pytest.raises(Exception):
        decrypt_sensitive(tampered)

    # Blind index is deterministic & case-insensitive
    assert blind_index("Alice@Example.com") == blind_index("  alice@example.com ")


def test_sqlite_sensitive_columns_encrypted_at_rest(tmp_path) -> None:
    db_file = str(tmp_path / "sec_test.db")
    repo = StorageRepository(db_path=db_file)
    repo.create_user("secuser", "sec@example.com", "hash", full_name="Secret Full Name")
    send_signup_confirmation_email("sec@example.com", "secuser", "Secret Full Name", storage_repo=repo)
    repo.save_pr_review(
        repo="org/sec",
        number=1,
        title="PR Title",
        author="secuser",
        head_sha="abc12345",
        review_res=ReviewResponse(
            summary="Sensitive finding summary",
            findings=[Finding(severity="high", category="security", title="T", description="D", line=1)],
            analyzed_lines=1,
            engine="heuristic-v1",
        ),
    )

    conn = sqlite3.connect(db_file)
    user_row = conn.execute("SELECT full_name FROM users WHERE username='secuser'").fetchone()
    email_row = conn.execute("SELECT body_html, body_text FROM sent_emails").fetchone()
    pr_row = conn.execute("SELECT summary, findings_json FROM pull_requests WHERE id='#1'").fetchone()
    conn.close()

    assert user_row[0].startswith(ENC_PREFIX)
    assert "Secret Full Name" not in user_row[0]
    assert email_row[0].startswith(ENC_PREFIX) and email_row[1].startswith(ENC_PREFIX)
    assert pr_row[0].startswith(ENC_PREFIX) and pr_row[1].startswith(ENC_PREFIX)

    # Transparent decryption on read
    reloaded = StorageRepository(db_path=db_file)
    assert reloaded.get_user_auth("secuser")[0].full_name == "Secret Full Name"
    assert "secuser" in reloaded.get_sent_emails("sec@example.com")[0].body_text
    assert reloaded.pull_requests["#1"].summary == "Sensitive finding summary"


def test_ssrf_and_rate_limit_guards() -> None:
    assert validate_github_identifier("Mahirlokare", "owner") == "Mahirlokare"
    for bad in ["../etc", "127.0.0.1", "a/b", "bad\\path"]:
        with pytest.raises(HTTPException):
            validate_github_identifier(bad, "owner")

    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.check("ip1")[0] is True
    assert limiter.check("ip1")[0] is True
    assert limiter.check("ip1")[0] is False

    guard = LoginBruteForceGuard(max_failures=2, lockout_seconds=60)
    guard.record_failure("u1")
    assert guard.is_locked("u1")[0] is False
    guard.record_failure("u1")
    assert guard.is_locked("u1")[0] is True
    guard.clear("u1")
    assert guard.is_locked("u1")[0] is False


def test_no_google_fonts_in_frontend() -> None:
    root = Path(__file__).resolve().parent.parent
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    css = (root / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html
    assert "fonts.googleapis.com" not in css
    assert "fonts.gstatic.com" not in css
    assert "Content-Security-Policy" in html
