"""REST endpoints for the `auth` module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from brasaland_api.core.deps import get_current_user
from brasaland_api.core.security import create_access_token, verify_password
from brasaland_api.modules.auth.schemas import CurrentUserOut, Token
from brasaland_api.modules.profiles import services as profile_services
from brasaland_api.modules.profiles.schemas import ProfileOut
from brasaland_api.modules.users import services as user_services
from brasaland_api.modules.users.models import UserRecord

router = APIRouter(prefix="/auth", tags=["auth"])


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


@router.get("/me", response_model=CurrentUserOut)
def read_current_user(current_user: UserRecord = Depends(get_current_user)) -> CurrentUserOut:
    profile = profile_services.get_profile_by_user_id(current_user.id)
    profile_out = (
        ProfileOut(id=profile.id, user_id=profile.user_id, name=profile.name, phone=profile.phone, address=profile.address)
        if profile
        else None
    )
    return CurrentUserOut(email=current_user.email, role=current_user.role, profile=profile_out)
