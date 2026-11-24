"""Unit tests for user authentication, password hashing, tokens, and confirmation emails."""
from app.services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.services.email_service import (
    send_signin_notification_email,
    send_signup_confirmation_email,
)
from app.storage.repository import StorageRepository


def test_password_hashing_and_verification() -> None:
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert ":" in hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_token_creation_and_decoding() -> None:
    token = create_access_token("usr_12345", "testuser", "test@example.com")
    assert isinstance(token, str)
    assert "." in token

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["uid"] == "usr_12345"
    assert decoded["usr"] == "testuser"
    assert decoded["eml"] == "test@example.com"

    # Corrupt token
    assert decode_access_token("bad.token") is None
    assert decode_access_token(token + "tampered") is None


def test_storage_user_crud_and_email_records(tmp_path) -> None:
    db_file = str(tmp_path / "test_auth.db")
    repo = StorageRepository(db_path=db_file)

    # 1. Create user
    pwd_hash = hash_password("mypassword")
    user = repo.create_user(
        username="alice_dev",
        email="alice@company.com",
        password_hash=pwd_hash,
        full_name="Alice Developer",
    )
    assert user.id.startswith("usr_")
    assert user.username == "alice_dev"
    assert user.email == "alice@company.com"

    # 2. Get user by auth
    auth_res = repo.get_user_auth("alice_dev")
    assert auth_res is not None
    u, stored_hash = auth_res
    assert u.id == user.id
    assert verify_password("mypassword", stored_hash) is True

    # 3. Get user by email
    auth_email = repo.get_user_auth("ALICE@company.com")
    assert auth_email is not None
    assert auth_email[0].id == user.id

    # 4. Dispatch signup confirmation email
    email_rec = send_signup_confirmation_email(
        to_email=user.email,
        username=user.username,
        full_name=user.full_name,
        storage_repo=repo,
    )
    assert email_rec.id.startswith("eml_")
    assert email_rec.recipient == "alice@company.com"
    assert "Confirm Your Account" in email_rec.subject
    assert "alice_dev" in email_rec.body_text

    # 5. Dispatch signin notification email
    signin_email = send_signin_notification_email(
        to_email=user.email,
        username=user.username,
        ip_address="192.168.1.10",
        storage_repo=repo,
    )
    assert signin_email.id.startswith("eml_")
    assert "Sign-In" in signin_email.subject

    # 6. Retrieve sent emails
    emails = repo.get_sent_emails(recipient="alice@company.com")
    assert len(emails) == 2
