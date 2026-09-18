"""REST endpoints for the `users` module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.profiles import services as profile_services
from brasaland_api.modules.users import services as user_services
from brasaland_api.modules.users.models import UserRecord, UserRole
from brasaland_api.modules.users.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate) -> UserOut:
    try:
        user = user_services.create_user(payload.email, payload.password, role=UserRole.USER)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    profile_services.create_profile(
        user.id, name=payload.name, phone=payload.phone, address=payload.address
    )
    return UserOut(id=user.id, email=user.email, is_active=user.is_active, role=user.role, created_at=user.created_at)


@router.get("", response_model=list[UserOut])
def list_users(current_user: UserRecord = Depends(get_current_user)) -> list[UserOut]:
    return [
        UserOut(id=u.id, email=u.email, is_active=u.is_active, role=u.role, created_at=u.created_at)
        for u in user_services.list_users()
    ]


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, current_user: UserRecord = Depends(get_current_user)) -> UserOut:
    user = user_services.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return UserOut(id=user.id, email=user.email, is_active=user.is_active, role=user.role, created_at=user.created_at)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str, payload: UserUpdate, current_user: UserRecord = Depends(get_current_user)
) -> UserOut:
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes modificar este usuario.")

    role_update = payload.role
    if role_update is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede cambiar el rol.")

    try:
        updated = user_services.update_user(user_id, email=payload.email, role=role_update)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return UserOut(
        id=updated.id, email=updated.email, is_active=updated.is_active, role=updated.role, created_at=updated.created_at
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, current_user: UserRecord = Depends(get_current_user)) -> None:
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes eliminar este usuario.")
    if not user_services.delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
