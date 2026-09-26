from __future__ import annotations

import pytest

from brasaland_api.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_verifies_original_password():
    hashed = hash_password("secret-password")
    assert hashed != "secret-password"
    assert verify_password("secret-password", hashed)


def test_password_hash_rejects_wrong_password():
    hashed = hash_password("secret-password")
    assert not verify_password("wrong-password", hashed)


def test_created_token_decodes_subject():
    token = create_access_token("user-123", expires_minutes=5)
    assert decode_access_token(token)["sub"] == "user-123"


@pytest.mark.parametrize("token", ["not-a-jwt", create_access_token("expired", expires_minutes=-1)])
def test_decode_rejects_malformed_or_expired_token(token):
    with pytest.raises(ValueError, match="Token inválido o expirado"):
        decode_access_token(token)


def test_decode_rejects_token_without_subject():
    from jose import jwt
    from brasaland_api.core.config import get_settings
    token = jwt.encode({"exp": 4102444800}, get_settings().secret_key, algorithm=get_settings().jwt_algorithm)
    assert decode_access_token(token).get("sub") is None