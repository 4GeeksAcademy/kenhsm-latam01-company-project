from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError

from brasaland_api.modules.auth import router as auth_router
from brasaland_api.modules.auth.schemas import CurrentUserOut
from brasaland_api.modules.profiles import services as profile_services
from brasaland_api.modules.users import router as users_router
from brasaland_api.modules.users import services as user_services
from brasaland_api.modules.users.models import UserRecord, UserRole
from brasaland_api.modules.users.schemas import UserCreate


def make_user(*, active: bool = True, role: UserRole = UserRole.USER) -> UserRecord:
    user = user_services.create_user("user@example.com", "correct-password", role=role)
    user.is_active = active
    if not active:
        from brasaland_api.core.db import users_table
        from tinydb import Query
        users_table().update({"is_active": False}, Query().id == user.id)
    return user


def test_register_creates_user_and_profile():
    result = users_router.register_user(UserCreate(email="new@example.com", password="password-123", name="Ana"))
    assert result.email == "new@example.com"
    assert profile_services.get_profile_by_user_id(result.id).name == "Ana"


def test_register_rejects_short_or_empty_password():
    with pytest.raises(ValidationError):
        UserCreate(email="new@example.com", password="")


def test_register_rejects_duplicate_email(monkeypatch):
    monkeypatch.setattr(user_services, "create_user", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("duplicated")))
    with pytest.raises(HTTPException) as error:
        users_router.register_user(UserCreate(email="duplicate@example.com", password="password-123"))
    assert error.value.status_code == 400


def test_login_returns_access_token_for_valid_credentials(monkeypatch):
    user = make_user()
    monkeypatch.setattr(auth_router.user_services, "get_user_by_email", lambda email: user)
    monkeypatch.setattr(auth_router, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(auth_router, "create_access_token", lambda subject: f"token-for-{subject}")
    result = auth_router.login(OAuth2PasswordRequestForm(username=user.email, password="correct-password"))
    assert result.access_token == f"token-for-{user.id}"
    assert result.token_type == "bearer"


@pytest.mark.parametrize("username,password", [("missing@example.com", "password"), ("user@example.com", "")])
def test_login_rejects_invalid_credentials(monkeypatch, username, password):
    monkeypatch.setattr(auth_router.user_services, "get_user_by_email", lambda email: None)
    with pytest.raises(HTTPException) as error:
        auth_router.login(OAuth2PasswordRequestForm(username=username, password=password))
    assert error.value.status_code == 401


def test_login_rejects_inactive_user(monkeypatch):
    user = make_user(active=False)
    monkeypatch.setattr(auth_router.user_services, "get_user_by_email", lambda email: user)
    monkeypatch.setattr(auth_router, "verify_password", lambda plain, hashed: True)
    with pytest.raises(HTTPException) as error:
        auth_router.login(OAuth2PasswordRequestForm(username=user.email, password="correct-password"))
    assert error.value.detail == "Usuario inactivo."


def test_read_current_user_returns_profile():
    user = make_user()
    profile_services.create_profile(user.id, name="Ana")
    result = auth_router.read_current_user(user)
    assert isinstance(result, CurrentUserOut)
    assert result.profile.name == "Ana"


def test_read_current_user_allows_missing_profile():
    user = make_user()
    assert auth_router.read_current_user(user).profile is None


def test_read_current_user_rejects_missing_user_argument():
    with pytest.raises((TypeError, AttributeError)):
        auth_router.read_current_user(None)