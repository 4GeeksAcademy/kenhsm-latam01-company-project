from __future__ import annotations

import pytest
from fastapi import HTTPException

from brasaland_api.core import deps
from brasaland_api.core.security import create_access_token
from brasaland_api.modules.users.models import UserRole


def test_get_current_user_resolves_valid_token(monkeypatch):
    expected = type("User", (), {"is_active": True})()
    monkeypatch.setattr(deps, "decode_access_token", lambda token: {"sub": "user-1"})
    monkeypatch.setattr(deps.user_services, "get_user_by_id", lambda user_id: expected)
    assert deps.get_current_user("valid") is expected


@pytest.mark.parametrize("payload", [{}, {"sub": "missing"}])
def test_get_current_user_rejects_missing_subject_or_unknown_user(monkeypatch, payload):
    monkeypatch.setattr(deps, "decode_access_token", lambda token: payload)
    monkeypatch.setattr(deps.user_services, "get_user_by_id", lambda user_id: None)
    with pytest.raises(HTTPException) as error:
        deps.get_current_user("invalid")
    assert error.value.status_code == 401


def test_get_current_user_rejects_malformed_token(monkeypatch):
    monkeypatch.setattr(deps, "decode_access_token", lambda token: (_ for _ in ()).throw(ValueError("bad token")))
    with pytest.raises(HTTPException) as error:
        deps.get_current_user("malformed")
    assert error.value.status_code == 401


def test_get_current_user_rejects_inactive_user(monkeypatch):
    monkeypatch.setattr(deps, "decode_access_token", lambda token: {"sub": "inactive"})
    monkeypatch.setattr(deps.user_services, "get_user_by_id", lambda user_id: type("User", (), {"is_active": False})())
    with pytest.raises(HTTPException) as error:
        deps.get_current_user("inactive-token")
    assert error.value.status_code == 401


def test_require_admin_rejects_non_admin():
    user = type("User", (), {"role": UserRole.USER})()
    with pytest.raises(HTTPException) as error:
        deps.require_admin(user)
    assert error.value.status_code == 403