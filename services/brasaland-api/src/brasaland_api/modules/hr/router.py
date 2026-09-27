"""Minimal HR endpoints (employees) protected by authentication."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.hr.schemas import EmployeeOut, EmployeeUpdate
from brasaland_api.modules.users.models import UserRecord

router = APIRouter(prefix="/hr", tags=["hr"])

_EMPLOYEES = {
    "EMP-001": {"id": "EMP-001", "name": "Felipe Guerrero", "location_id": "COL-01", "salary_usd": 2400},
    "EMP-002": {"id": "EMP-002", "name": "Jake Morrison", "location_id": "FLA-01", "salary_usd": 2100},
}


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(current_user: UserRecord = Depends(get_current_user)) -> list[EmployeeOut]:
    return [EmployeeOut(**employee) for employee in _EMPLOYEES.values()]


@router.put("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: str, payload: EmployeeUpdate, current_user: UserRecord = Depends(get_current_user)
) -> EmployeeOut:
    employee = _EMPLOYEES.get(employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado.")
    updates = payload.model_dump(exclude_none=True)
    employee.update(updates)
    return EmployeeOut(**employee)
