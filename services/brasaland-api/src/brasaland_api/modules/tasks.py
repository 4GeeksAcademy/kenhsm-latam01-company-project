"""Authenticated inspection of Celery task state."""

from __future__ import annotations

from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, Depends

from brasaland_api.celery_app import celery_app
from brasaland_api.core.deps import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])
CELERY_STATUS = {
    "PENDING": "pending",
    "RECEIVED": "pending",
    "RETRY": "pending",
    "STARTED": "started",
    "SUCCESS": "success",
    "FAILURE": "failure",
}


@router.get("/{task_id}")
def get_task_status(task_id: str) -> dict[str, Any]:
    task = AsyncResult(task_id, app=celery_app)
    task_status = CELERY_STATUS.get(task.state, "pending")
    result = task.result if task_status == "success" else None
    if task_status == "failure":
        result = {"error": str(task.result)}
    return {"task_id": task_id, "status": task_status, "result": result}