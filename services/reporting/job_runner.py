"""PostgREST persistence for independent background job runs."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timezone
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class JobRunStoreError(RuntimeError):
    """The job-run or telemetry request could not be completed."""


class JobRunStore:
    def __init__(
        self,
        supabase_url: str,
        api_key: str,
        *,
        bearer_token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> JobRunStore:
        supabase_url = os.getenv("SUPABASE_URL")
        secret_key = os.getenv("SUPABASE_SECRET_KEY")
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        api_key = secret_key or service_role_key
        if not supabase_url or not api_key:
            raise JobRunStoreError(
                "SUPABASE_URL and SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY are required"
            )
        return cls(
            supabase_url,
            api_key,
            bearer_token=None if secret_key else service_role_key,
        )

    def _request(
        self,
        method: str,
        table: str,
        *,
        query: list[tuple[str, str]] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.supabase_url}/rest/v1/{table}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {
            "apikey": self.api_key,
            "Accept": "application/json",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Prefer"] = "return=representation"
        request = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_body = response.read()
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise JobRunStoreError(
                f"Supabase {method} {table} failed (HTTP {error.code}): {detail}"
            ) from error
        except URLError as error:
            raise JobRunStoreError(f"Supabase {method} {table} request failed: {error.reason}") from error

        if not response_body:
            return None
        try:
            return json.loads(response_body)
        except json.JSONDecodeError as error:
            raise JobRunStoreError(f"Supabase {method} {table} returned invalid JSON") from error

    def has_processing_lock(self, job_name: str) -> bool:
        rows = self._request(
            "GET",
            "job_runs",
            query=[
                ("job_name", f"eq.{job_name}"),
                ("status", "eq.processing"),
                ("select", "id"),
                ("limit", "1"),
            ],
        )
        return bool(rows)

    def has_completed_for_date(self, job_name: str, target_date: date) -> bool:
        rows = self._request(
            "GET",
            "job_runs",
            query=[
                ("job_name", f"eq.{job_name}"),
                ("target_date", f"eq.{target_date.isoformat()}"),
                ("status", "eq.completed"),
                ("select", "id"),
                ("limit", "1"),
            ],
        )
        return bool(rows)

    def create_pending(self, job_name: str, target_date: date) -> str:
        rows = self._request(
            "POST",
            "job_runs",
            payload={
                "job_name": job_name,
                "target_date": target_date.isoformat(),
                "status": "pending",
            },
        )
        if not isinstance(rows, list) or not rows or not rows[0].get("id"):
            raise JobRunStoreError("Supabase did not return the created job_run id")
        return str(rows[0]["id"])

    def mark_processing(self, run_id: str) -> None:
        rows = self._request(
            "PATCH",
            "job_runs",
            query=[("id", f"eq.{run_id}"), ("status", "eq.pending")],
            payload={
                "status": "processing",
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if not isinstance(rows, list) or not rows:
            raise JobRunStoreError("The pending job_run could not transition to processing")

    def mark_completed(self, run_id: str) -> None:
        self._update_final_state(run_id, "completed", error_message=None)

    def mark_failed(self, run_id: str, error_message: str) -> None:
        self._update_final_state(run_id, "failed", error_message=error_message[:4000])

    def _update_final_state(self, run_id: str, status: str, *, error_message: str | None) -> None:
        rows = self._request(
            "PATCH",
            "job_runs",
            query=[("id", f"eq.{run_id}")],
            payload={
                "status": status,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error_message": error_message,
            },
        )
        if not isinstance(rows, list) or not rows:
            raise JobRunStoreError(f"The job_run could not transition to {status}")

    def iter_telemetry_events(self, target_date: date, *, page_size: int = 1000) -> Iterator[dict[str, Any]]:
        start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        end = datetime.combine(date.fromordinal(target_date.toordinal() + 1), time.min, tzinfo=timezone.utc)
        start_text = start.isoformat().replace("+00:00", "Z")
        end_text = end.isoformat().replace("+00:00", "Z")
        offset = 0

        while True:
            rows = self._request(
                "GET",
                "telemetry_events",
                query=[
                    ("select", "timestamp,service,event_type,level,value,message,tags"),
                    ("timestamp", f"gte.{start_text}"),
                    ("timestamp", f"lt.{end_text}"),
                    ("order", "timestamp.asc"),
                    ("limit", str(page_size)),
                    ("offset", str(offset)),
                ],
            )
            if not isinstance(rows, list):
                raise JobRunStoreError("Supabase returned an invalid telemetry response")
            yield from rows
            if len(rows) < page_size:
                return
            offset += len(rows)