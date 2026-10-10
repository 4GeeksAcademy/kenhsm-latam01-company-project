"""Supabase access and local structured run metadata for business reporting."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import httpx


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUN_LOG_PATH = REPOSITORY_ROOT / "data" / "eval" / "pipeline_runs.jsonl"
LOCAL_REPORT_PATH = REPOSITORY_ROOT / "data" / "eval" / "weekly_location_performance.json"


def supabase_url() -> str | None:
    value = os.getenv("SUPABASE_URL")
    return value.rstrip("/") if value else None


def read_key() -> str | None:
    return os.getenv("SUPABASE_REPORTING_READ_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def write_key() -> str | None:
    return os.getenv("SUPABASE_REPORTING_WRITE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def has_supabase_configuration() -> bool:
    return bool(supabase_url() and read_key() and write_key())


def _headers(key: str, schema: str = "public") -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept-Profile": schema,
        "Content-Profile": schema,
        "Content-Type": "application/json",
    }


def extract_week_events(week_start: date) -> list[dict[str, Any]]:
    url = supabase_url()
    key = read_key()
    if not url or not key:
        raise RuntimeError("Supabase reporting read credentials are not configured")

    from data.process.weekly_performance import iso_week_bounds

    lower_bound, upper_bound = iso_week_bounds(week_start)
    params = {
        "select": "id,timestamp,event_type,tags",
        "timestamp": f"gte.{lower_bound.isoformat()}",
        "event_type": "in.(inbound_order_created,stock_waste_registered,stock_threshold_triggered,ingredient_price_variance_detected)",
        "order": "timestamp.asc,id.asc",
    }
    rows: list[dict[str, Any]] = []
    offset = 0
    with httpx.Client(timeout=30.0) as client:
        while True:
            response = client.get(
                f"{url}/rest/v1/telemetry_events",
                params={**params, "timestamp": f"gte.{lower_bound.isoformat()}", "and": f"(timestamp.lt.{upper_bound.isoformat()})"},
                headers={**_headers(key), "Range": f"{offset}-{offset + 999}"},
            )
            response.raise_for_status()
            page = response.json()
            if not isinstance(page, list):
                raise RuntimeError("Supabase returned an invalid telemetry response")
            rows.extend(page)
            if len(page) < 1000:
                break
            offset += len(page)
    return rows


def load_weekly_performance(rows: list[dict[str, Any]]) -> int:
    url = supabase_url()
    key = write_key()
    if not url or not key:
        raise RuntimeError("Supabase reporting write credentials are not configured")
    if not rows:
        return 0

    response = httpx.post(
        f"{url}/rest/v1/weekly_location_performance",
        params={"on_conflict": "location_id,week_start"},
        json=rows,
        headers={
            **_headers(key, "reporting"),
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return len(rows)


def persist_run_metadata(record: dict[str, Any], *, local_mode: bool) -> None:
    RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
    descriptor = os.open(RUN_LOG_PATH, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, serialized.encode("utf-8"))
    finally:
        os.close(descriptor)

    if local_mode:
        return
    url = supabase_url()
    key = write_key()
    if not url or not key:
        raise RuntimeError("Supabase reporting write credentials are not configured")
    response = httpx.post(
        f"{url}/rest/v1/pipeline_runs",
        params={"on_conflict": "run_id"},
        json=[record],
        headers={
            **_headers(key, "reporting"),
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        timeout=15.0,
    )
    response.raise_for_status()


def write_local_report(rows: list[dict[str, Any]]) -> None:
    LOCAL_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_REPORT_PATH.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def _latest_local_run() -> dict[str, Any] | None:
    if not RUN_LOG_PATH.exists():
        return None
    latest = None
    with RUN_LOG_PATH.open(encoding="utf-8") as run_log:
        for line in run_log:
            if line.strip():
                latest = json.loads(line)
    return latest


def get_latest_pipeline_run() -> dict[str, Any] | None:
    url = supabase_url()
    key = read_key()
    if url and key:
        try:
            response = httpx.get(
                f"{url}/rest/v1/pipeline_runs",
                params={"select": "*", "order": "started_at.desc", "limit": "1"},
                headers=_headers(key, "reporting"),
                timeout=10.0,
            )
            response.raise_for_status()
            records = response.json()
            return records[0] if records else None
        except httpx.HTTPError:
            pass
    return _latest_local_run()


def query_weekly_location_performance(week_start: date | None = None) -> dict[str, Any] | None:
    url = supabase_url()
    key = read_key()
    if url and key:
        headers = _headers(key, "reporting")
        with httpx.Client(timeout=10.0) as client:
            if week_start is None:
                latest = client.get(
                    f"{url}/rest/v1/weekly_location_performance",
                    params={"select": "week_start", "order": "week_start.desc", "limit": "1"},
                    headers=headers,
                )
                latest.raise_for_status()
                latest_rows = latest.json()
                if not latest_rows:
                    return None
                week_start = date.fromisoformat(latest_rows[0]["week_start"])
            response = client.get(
                f"{url}/rest/v1/weekly_location_performance",
                params={
                    "select": "location_id,country,week_start,total_purchase_cost,total_waste_cost,waste_ratio,stockout_events_count,price_alert_events_count,currency",
                    "week_start": f"eq.{week_start.isoformat()}",
                    "order": "country.asc,location_id.asc",
                },
                headers=headers,
            )
            response.raise_for_status()
            rows = response.json()
            return {"week_start": week_start.isoformat(), "locations": rows} if rows else None

    if not LOCAL_REPORT_PATH.exists():
        return None
    local_rows = json.loads(LOCAL_REPORT_PATH.read_text(encoding="utf-8"))
    if not local_rows:
        return None
    if week_start is None:
        week_start = max(date.fromisoformat(row["week_start"]) for row in local_rows)
    selected = [row for row in local_rows if row["week_start"] == week_start.isoformat()]
    return {"week_start": week_start.isoformat(), "locations": selected} if selected else None