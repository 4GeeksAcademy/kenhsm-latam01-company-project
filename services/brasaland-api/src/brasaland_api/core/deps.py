"""FastAPI dependency that resolves the authenticated user from a bearer token."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from brasaland_api.core.security import decode_access_token
from brasaland_api.modules.users import services as user_services
from brasaland_api.modules.users.models import UserRecord

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserRecord:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except ValueError as error:
        raise credentials_error from error

    user_uuid = payload.get("sub")
    if not user_uuid:
        raise credentials_error

    user = user_services.get_user_by_id(user_uuid)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_admin(current_user: UserRecord = Depends(get_current_user)) -> UserRecord:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de administrador.")
    return current_user
