"""REST endpoints for the `profiles` module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.profiles import services as profile_services
from brasaland_api.modules.profiles.schemas import ProfileOut, ProfileUpdate
from brasaland_api.modules.users.models import UserRecord

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=ProfileOut)
def read_my_profile(current_user: UserRecord = Depends(get_current_user)) -> ProfileOut:
    profile = profile_services.get_profile_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado.")
    return ProfileOut(id=profile.id, user_id=profile.user_id, name=profile.name, phone=profile.phone, address=profile.address)


@router.put("/me", response_model=ProfileOut)
def update_my_profile(payload: ProfileUpdate, current_user: UserRecord = Depends(get_current_user)) -> ProfileOut:
    profile = profile_services.update_profile(
        current_user.id, name=payload.name, phone=payload.phone, address=payload.address
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado.")
    return ProfileOut(id=profile.id, user_id=profile.user_id, name=profile.name, phone=profile.phone, address=profile.address)
