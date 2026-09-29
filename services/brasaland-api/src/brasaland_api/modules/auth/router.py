"""REST endpoints for the `auth` module."""

from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from brasaland_api.core.config import get_settings
from brasaland_api.core.deps import get_current_user
from brasaland_api.core.security import create_access_token, hash_password, verify_password
from brasaland_api.modules.auth.password_reset import (
    consume_reset_token,
    create_reset_token,
    send_password_reset_email,
)
from brasaland_api.modules.auth.schemas import (
    AuthMessage,
    ChangePasswordRequest,
    CurrentUserOut,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
)
from brasaland_api.modules.profiles import services as profile_services
from brasaland_api.modules.profiles.schemas import ProfileOut
from brasaland_api.modules.users import services as user_services
from brasaland_api.modules.users.models import UserRecord

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user = user_services.get_user_by_email(form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo.")

    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token)


@router.post("/forgot-password", response_model=AuthMessage)
def forgot_password(payload: ForgotPasswordRequest) -> AuthMessage:
    user = user_services.get_user_by_email(str(payload.email))
    if user is not None:
        token, _ = create_reset_token(user.id)
        settings = get_settings()
        reset_url = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={quote(token, safe='')}"
        try:
            send_password_reset_email(user.email, reset_url)
        except Exception:
            logger.exception("No se pudo enviar el correo de restablecimiento.")

    return AuthMessage(message="Si esa dirección está registrada, recibirás un enlace en breve.")


@router.post("/reset-password", response_model=AuthMessage)
def reset_password(payload: ResetPasswordRequest) -> AuthMessage:
    try:
        consume_reset_token(payload.token, payload.new_password)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return AuthMessage(message="Contraseña actualizada correctamente.")


@router.post("/change-password", response_model=AuthMessage)
def change_password(
    payload: ChangePasswordRequest,
    current_user: UserRecord = Depends(get_current_user),
) -> AuthMessage:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña actual es incorrecta.")
    if not user_services.update_password(current_user.id, hash_password(payload.new_password)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El usuario ya no existe.")
    return AuthMessage(message="Contraseña actualizada correctamente.")


@router.get("/me", response_model=CurrentUserOut)
def read_current_user(current_user: UserRecord = Depends(get_current_user)) -> CurrentUserOut:
    profile = profile_services.get_profile_by_user_id(current_user.id)
    profile_out = (
        ProfileOut(id=profile.id, user_id=profile.user_id, name=profile.name, phone=profile.phone, address=profile.address)
        if profile
        else None
    )
    return CurrentUserOut(email=current_user.email, role=current_user.role, profile=profile_out)
