"""Persistence for exhausted Celery tasks."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from brasaland_api.core.config import Settings, get_settings
from brasaland_api.core.supabase_auth import supabase_auth_headers


def record_dead_letter(
    task_id: str,
    task_name: str,
    attempt: int,
    error_message: str,
    *,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    auth_headers = supabase_auth_headers(settings)
    if not settings.supabase_url or auth_headers is None:
        raise RuntimeError("Supabase storage is not configured for the task DLQ")

    response = httpx.post(
        f"{settings.supabase_url.rstrip('/')}/rest/v1/task_dead_letters",
        params={"on_conflict": "task_id"},
        json={
            "task_id": task_id,
            "task_name": task_name,
            "attempt": attempt,
            "error_message": error_message[:10000],
            "failed_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={
            **auth_headers,
            "Content-Type": "application/json",
            "Accept-Profile": "public",
            "Content-Profile": "public",
            "Prefer": "resolution=ignore-duplicates,return=minimal",
        },
        timeout=15.0,
    )
    response.raise_for_status()