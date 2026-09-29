"""Password hashing and JWT helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from typing import Any

from jose import JWTError, jwt
from passlib.hash import bcrypt

from brasaland_api.core.config import get_settings


def hash_password(plain_password: str) -> str:
    return bcrypt.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    expire_delta = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    expire_at = datetime.now(timezone.utc) + expire_delta
    payload: dict[str, Any] = {"sub": subject, "exp": expire_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as error:
        raise ValueError("Token inválido o expirado.") from error


def create_password_reset_token(
    subject: str, expires_minutes: int | None = None
) -> tuple[str, str, datetime]:
    settings = get_settings()
    token_id = str(uuid.uuid4())
    lifetime = settings.password_reset_token_expire_minutes if expires_minutes is None else expires_minutes
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=lifetime)
    payload: dict[str, Any] = {
        "sub": subject,
        "jti": token_id,
        "purpose": "password_reset",
        "exp": expire_at,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, token_id, expire_at


def decode_password_reset_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as error:
        raise ValueError("El enlace de restablecimiento es inválido o ha expirado.") from error

    if payload.get("purpose") != "password_reset" or not payload.get("sub") or not payload.get("jti"):
        raise ValueError("El enlace de restablecimiento es inválido o ha expirado.")
    return payload
