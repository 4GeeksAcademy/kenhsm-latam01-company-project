"""Export yesterday's telemetry and run the existing reporting pipeline."""

from __future__ import annotations

import csv
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from services.reporting.job_runner import JobRunStore, JobRunStoreError


JOB_NAME = "nightly_export"
CSV_FIELDS = ("timestamp", "service", "event_type", "level", "value", "message", "tags")
PIPELINE_COMMAND = (sys.executable, "data/pipelines/pipeline.py")
LOGGER = logging.getLogger("brasaland.nightly_export")


def _log(
    level: int,
    status: str,
    message: str,
    *args: Any,
    exc_info: bool = False,
) -> None:
    LOGGER.log(
        level,
        message,
        *args,
        extra={"job_name": JOB_NAME, "job_status": status},
        exc_info=exc_info,
    )


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s job=%(job_name)s status=%(job_status)s %(levelname)s %(message)s",
    )


def resolve_target_date(value: str | None = None, *, now: datetime | None = None) -> date:
    raw_value = value if value is not None else os.getenv("TARGET_DATE")
    if raw_value:
        try:
            parsed_date = date.fromisoformat(raw_value)
        except ValueError as error:
            raise ValueError("TARGET_DATE must use YYYY-MM-DD format") from error
        if parsed_date.isoformat() != raw_value:
            raise ValueError("TARGET_DATE must use YYYY-MM-DD format")
        return parsed_date
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return current_time.astimezone(timezone.utc).date() - timedelta(days=1)


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def export_telemetry_csv(
    store: JobRunStore,
    target_date: date,
    destination: Path,
) -> bool:
    """Write a complete snapshot without replacing an existing day's export."""
    if destination.exists():
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            writer = csv.DictWriter(temporary_file, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for event in store.iter_telemetry_events(target_date):
                writer.writerow({field: _csv_value(event.get(field)) for field in CSV_FIELDS})
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        try:
            os.link(temporary_path, destination)
        except FileExistsError:
            return False
        return True
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def run_nightly_export(
    *,
    target_date: date,
    store: JobRunStore,
    repo_root: Path,
    subprocess_run: Callable[..., Any] = subprocess.run,
) -> int:
    if store.has_processing_lock(JOB_NAME):
        _log(logging.INFO, "skipped", "Another nightly_export run is already processing")
        return 0
    if store.has_completed_for_date(JOB_NAME, target_date):
        _log(logging.INFO, "skipped", "A completed run already exists for target_date=%s", target_date)
        return 0

    run_id = store.create_pending(JOB_NAME, target_date)
    try:
        try:
            store.mark_processing(run_id)
        except JobRunStoreError:
            if not store.has_processing_lock(JOB_NAME):
                raise
            store.mark_failed(run_id, "Skipped because another nightly_export run holds the processing lock")
            _log(logging.INFO, "skipped", "Another nightly_export run acquired the processing lock")
            return 0

        if store.has_completed_for_date(JOB_NAME, target_date):
            store.mark_completed(run_id)
            _log(logging.INFO, "completed", "Duplicate target_date=%s omitted", target_date)
            return 0

        csv_path = repo_root / "data" / "raw" / f"telemetry_{target_date.isoformat()}.csv"
        exported = export_telemetry_csv(store, target_date, csv_path)
        _log(
            logging.INFO,
            "processing",
            "Telemetry CSV %s: %s",
            "created" if exported else "already exists",
            csv_path,
        )
        subprocess_run(PIPELINE_COMMAND, cwd=repo_root, check=True)
        store.mark_completed(run_id)
        _log(logging.INFO, "completed", "Nightly export completed for target_date=%s", target_date)
        return 0
    except Exception as error:
        try:
            store.mark_failed(run_id, str(error) or error.__class__.__name__)
        except Exception:
            _log(logging.ERROR, "failed", "Could not persist the failed job_run state", exc_info=True)
        _log(logging.ERROR, "failed", "Nightly export failed: %s", error, exc_info=True)
        raise


def main() -> int:
    configure_logging()
    try:
        target_date = resolve_target_date()
        store = JobRunStore.from_env()
        repo_root = Path(__file__).resolve().parents[1]
        _log(logging.INFO, "pending", "Starting nightly export for target_date=%s", target_date)
        return run_nightly_export(target_date=target_date, store=store, repo_root=repo_root)
    except Exception as error:
        _log(logging.ERROR, "failed", "Nightly export could not start: %s", error, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())