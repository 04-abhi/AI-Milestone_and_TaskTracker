"""Unit tests for security utilities."""
import pytest
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)


def test_password_hash_and_verify():
    plain = "SuperSecret123"
    hashed = get_password_hash(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_create_and_verify_access_token():
    token = create_access_token(subject=42)
    subject = verify_token(token, "access")
    assert subject == "42"


def test_create_and_verify_refresh_token():
    token = create_refresh_token(subject=99)
    subject = verify_token(token, "refresh")
    assert subject == "99"


def test_wrong_token_type_rejected():
    access = create_access_token(subject=1)
    # Trying to use access token as refresh token should fail
    assert verify_token(access, "refresh") is None


def test_invalid_token_returns_none():
    assert verify_token("not.a.valid.token") is None
    assert verify_token("") is None
