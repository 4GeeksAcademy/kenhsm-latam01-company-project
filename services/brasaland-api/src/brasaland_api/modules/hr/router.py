"""Minimal HR endpoints (employees) protected by authentication."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
<<<<<<< HEAD
from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.hr.schemas import EmployeeOut, EmployeeUpdate
=======
from pydantic import BaseModel

from brasaland_api.core.deps import get_current_user
>>>>>>> origin/main
from brasaland_api.modules.users.models import UserRecord

router = APIRouter(prefix="/hr", tags=["hr"])

_EMPLOYEES = {
    "EMP-001": {"id": "EMP-001", "name": "Felipe Guerrero", "location_id": "COL-01", "salary_usd": 2400},
    "EMP-002": {"id": "EMP-002", "name": "Jake Morrison", "location_id": "FLA-01", "salary_usd": 2100},
}


<<<<<<< HEAD
@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(current_user: UserRecord = Depends(get_current_user)) -> list[EmployeeOut]:
    return [EmployeeOut(**employee) for employee in _EMPLOYEES.values()]


@router.put("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: str, payload: EmployeeUpdate, current_user: UserRecord = Depends(get_current_user)
) -> EmployeeOut:
=======
class EmployeeUpdate(BaseModel):
    location_id: str | None = None
    salary_usd: float | None = None


@router.get("/employees")
def list_employees(current_user: UserRecord = Depends(get_current_user)) -> list[dict]:
    return list(_EMPLOYEES.values())


@router.put("/employees/{employee_id}")
def update_employee(
    employee_id: str, payload: EmployeeUpdate, current_user: UserRecord = Depends(get_current_user)
) -> dict:
>>>>>>> origin/main
    employee = _EMPLOYEES.get(employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado.")
    updates = payload.model_dump(exclude_none=True)
    employee.update(updates)
<<<<<<< HEAD
    return EmployeeOut(**employee)
=======
    return employee
>>>>>>> origin/main
