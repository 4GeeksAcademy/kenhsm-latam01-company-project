from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from scripts.nightly_export import (
    export_telemetry_csv,
    resolve_target_date,
    run_nightly_export,
)
from services.reporting.job_runner import JobRunStoreError


def test_resolve_target_date_uses_previous_utc_day() -> None:
    assert resolve_target_date(
        now=datetime(2026, 1, 1, 0, 15, tzinfo=timezone.utc)
    ) == date(2025, 12, 31)


def test_resolve_target_date_accepts_override_and_rejects_invalid_date() -> None:
    assert resolve_target_date("2026-03-08") == date(2026, 3, 8)
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        resolve_target_date("03/08/2026")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        resolve_target_date("20260308")


def test_export_writes_snapshot_once_and_serializes_tags(tmp_path: Path) -> None:
    store = Mock()
    store.iter_telemetry_events.return_value = iter(
        [{"event_type": "login", "tags": {"attempt": 1}, "timestamp": "2026-03-08T12:00:00Z"}]
    )
    destination = tmp_path / "telemetry_2026-03-08.csv"

    assert export_telemetry_csv(store, date(2026, 3, 8), destination) is True
    assert export_telemetry_csv(store, date(2026, 3, 8), destination) is False
    store.iter_telemetry_events.assert_called_once_with(date(2026, 3, 8))

    with destination.open(encoding="utf-8", newline="") as csv_file:
        row = next(csv.DictReader(csv_file))
    assert row["event_type"] == "login"
    assert json.loads(row["tags"]) == {"attempt": 1}


def test_run_skips_completed_date_without_export_or_pipeline(tmp_path: Path) -> None:
    store = Mock()
    store.has_processing_lock.return_value = False
    store.has_completed_for_date.return_value = True
    pipeline = Mock()

    assert run_nightly_export(
        target_date=date(2026, 3, 8), store=store, repo_root=tmp_path, subprocess_run=pipeline
    ) == 0

    store.create_pending.assert_not_called()
    pipeline.assert_not_called()


def test_run_marks_failed_and_propagates_pipeline_error(tmp_path: Path) -> None:
    store = Mock()
    store.has_processing_lock.return_value = False
    store.has_completed_for_date.return_value = False
    store.iter_telemetry_events.return_value = iter([])
    store.create_pending.return_value = "run-1"
    pipeline = Mock(side_effect=RuntimeError("pipeline failed"))

    with pytest.raises(RuntimeError, match="pipeline failed"):
        run_nightly_export(
            target_date=date(2026, 3, 8), store=store, repo_root=tmp_path, subprocess_run=pipeline
        )

    store.mark_processing.assert_called_once_with("run-1")
    store.mark_failed.assert_called_once_with("run-1", "pipeline failed")
    store.mark_completed.assert_not_called()


def test_run_skips_when_another_instance_wins_lock(tmp_path: Path) -> None:
    store = Mock()
    store.has_processing_lock.side_effect = [False, True]
    store.has_completed_for_date.return_value = False
    store.iter_telemetry_events.return_value = iter([])
    store.create_pending.return_value = "run-1"
    store.mark_processing.side_effect = JobRunStoreError("unique processing index")
    pipeline = Mock()

    assert run_nightly_export(
        target_date=date(2026, 3, 8), store=store, repo_root=tmp_path, subprocess_run=pipeline
    ) == 0

    store.mark_failed.assert_called_once()
    pipeline.assert_not_called()