"""Weekly Brasaland purchase, waste, stockout, and price-alert reporting flow.

Run from the repository root with ``python data/pipelines/pipeline.py``. Without
Supabase credentials this command uses the explicitly local JSON fixture and
writes validation output under ``data/eval``; deployed runs require Supabase.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from prefect import flow, get_run_logger, task
from prefect.tasks import task_input_hash

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from data.pipelines import run_store
from data.process.weekly_performance import transform_weekly_location_metrics

LOCAL_SOURCE_PATH = REPOSITORY_ROOT / "data" / "raw" / "telemetry_events.json"


@task(retries=3, retry_delay_seconds=5)
def extract_weekly_telemetry_events(week_start: str, *, local_mode: bool = False) -> list[dict[str, Any]]:
    """Read one complete ISO week; three retries absorb transient REST failures."""
    if local_mode:
        if not LOCAL_SOURCE_PATH.exists():
            return []
        source = json.loads(LOCAL_SOURCE_PATH.read_text(encoding="utf-8"))
        if not isinstance(source, list):
            raise ValueError("local telemetry fixture must be a JSON array")
        return source
    return run_store.extract_week_events(date.fromisoformat(week_start))


@task(cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=1))
def transform_weekly_location_metrics_task(
    events: list[dict[str, Any]], week_start: str
) -> list[dict[str, Any]]:
    # Prefect hashes the immutable event batch and week; a validated result stays reusable for one hour.
    return transform_weekly_location_metrics(events, week_start)


@task(retries=3, retry_delay_seconds=10)
def upsert_weekly_location_performance(
    rows: list[dict[str, Any]], *, local_mode: bool = False
) -> int:
    """Replace each location/week row; three retries tolerate transient PostgREST failures."""
    if local_mode:
        run_store.write_local_report(rows)
        return len(rows)
    computed_at = datetime.now(timezone.utc).isoformat()
    payload = [{**row, "computed_at": computed_at} for row in rows]
    return run_store.load_weekly_performance(payload)


@task(retries=3, retry_delay_seconds=5)
def persist_pipeline_run(record: dict[str, Any], *, local_mode: bool = False) -> None:
    """Persist run state; three retries absorb short reporting-store interruptions."""
    run_store.persist_run_metadata(record, local_mode=local_mode)


@task
def write_eval_snapshot(rows: list[dict[str, Any]], week_start: str) -> str:
    """Write a secondary validation artifact; this task is deliberately non-critical."""
    snapshot_path = REPOSITORY_ROOT / "data" / "eval" / f"weekly_location_performance_{week_start}.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return str(snapshot_path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count_events(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        event_type = str(event.get("event_type", "unknown"))
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts


@flow(name="weekly_location_performance_flow")
def weekly_location_performance_flow(
    week_start: date | str | None = None,
    trigger_type: str = "scheduled",
    run_id: str | None = None,
    local_mode: bool = False,
) -> dict[str, Any]:
    """Extract, validate, aggregate, and idempotently publish one ISO week."""
    logger = get_run_logger()
    if week_start is None:
        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday() + 7)
    if isinstance(week_start, date):
        week_start = week_start.isoformat()
    if date.fromisoformat(week_start).weekday() != 0:
        raise ValueError("week_start must be a Monday")

    started_at = _utc_now()
    execution_id = run_id or str(uuid4())
    record: dict[str, Any] = {
        "run_id": execution_id,
        "flow_name": "weekly_location_performance_flow",
        "trigger_type": trigger_type,
        "week_start": week_start,
        "status": "Running",
        "phase": "extract",
        "started_at": started_at,
        "ended_at": None,
        "source_counts": {},
        "source_min_timestamp": None,
        "source_max_timestamp": None,
        "source_watermark": None,
        "output_rows": 0,
        "records_processed": 0,
        "error_code": None,
        "error_message": None,
        "errors": [],
        "local_mode": local_mode,
    }
    events: list[dict[str, Any]] = []

    try:
        persist_pipeline_run(record, local_mode=local_mode)
        extraction_state = extract_weekly_telemetry_events(
            week_start, local_mode=local_mode, return_state=True
        )
        if not extraction_state.is_completed():
            extraction_state.result()
        events = extraction_state.result()
        record["records_processed"] = len(events)
        record["source_counts"] = _count_events(events)
        source_timestamps = [str(event["timestamp"]) for event in events if event.get("timestamp")]
        record["source_min_timestamp"] = min(source_timestamps) if source_timestamps else None
        record["source_max_timestamp"] = max(source_timestamps) if source_timestamps else None
        record["source_watermark"] = record["source_max_timestamp"]

        record["phase"] = "transform"
        rows = transform_weekly_location_metrics_task(events, week_start)
        record["phase"] = "load"
        record["output_rows"] = upsert_weekly_location_performance(
            rows, local_mode=local_mode
        )

        snapshot_state = write_eval_snapshot(rows, week_start, return_state=True)
        if not snapshot_state.is_completed():
            record["errors"].append(
                f"optional_eval_snapshot: {snapshot_state.message or 'task failed'}"
            )
            logger.warning("Optional evaluation snapshot failed; reporting load remains complete")

        record["status"] = "Completed"
        record["phase"] = "complete"
        record["ended_at"] = _utc_now()
        record["error_message"] = "; ".join(record["errors"]) or None
        persist_pipeline_run(record, local_mode=local_mode)
        return record
    except Exception as error:
        record["status"] = "Failed"
        record["ended_at"] = _utc_now()
        record["error_code"] = type(error).__name__
        record["error_message"] = str(error)[:500]
        record["errors"].append(record["error_message"])
        failed_audit = persist_pipeline_run(record, local_mode=local_mode, return_state=True)
        if not failed_audit.is_completed():
            logger.error("Could not persist final pipeline metadata after failure")
        logger.exception("Weekly location performance flow failed in phase %s", record["phase"])
        raise


def trigger_weekly_location_performance_flow(
    *, week_start: date | str | None = None, run_id: str | None = None
) -> dict[str, Any]:
    """Entry point shared by the API and the command line."""
    return weekly_location_performance_flow(
        week_start=week_start,
        trigger_type="manual",
        run_id=run_id,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Brasaland's weekly business reporting pipeline")
    parser.add_argument("--week-start", help="Monday date (YYYY-MM-DD); defaults to the previous complete ISO week")
    arguments = parser.parse_args()
    local_mode = not run_store.has_supabase_configuration()
    result = weekly_location_performance_flow(
        week_start=arguments.week_start,
        trigger_type="cli",
        local_mode=local_mode,
    )
    print(json.dumps(result, indent=2))
    if local_mode:
        print("Local validation mode: no Supabase reporting tables were modified.")


if __name__ == "__main__":
    main()