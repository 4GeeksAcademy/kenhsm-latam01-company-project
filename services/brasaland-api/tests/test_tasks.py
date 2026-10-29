from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from brasaland_api.celery_app import celery_app, generate_rfp_draft_task
from brasaland_api.core.deps import get_current_user
from brasaland_api.main import app


@pytest.mark.parametrize(
    ("celery_state", "celery_result", "expected_status", "expected_result"),
    [
        ("PENDING", None, "pending", None),
        ("STARTED", None, "started", None),
        ("SUCCESS", {"ticket_id": "ticket-1"}, "success", {"ticket_id": "ticket-1"}),
        ("FAILURE", RuntimeError("model unavailable"), "failure", {"error": "model unavailable"}),
    ],
)
def test_task_status_endpoint_maps_celery_states(celery_state, celery_result, expected_status, expected_result):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    try:
        with patch(
            "brasaland_api.modules.tasks.AsyncResult",
            return_value=SimpleNamespace(state=celery_state, result=celery_result),
        ):
            response = TestClient(app).get("/tasks/task-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"task_id": "task-1", "status": expected_status, "result": expected_result}


def test_celery_task_uses_retry_and_started_tracking_configuration():
    assert generate_rfp_draft_task.max_retries == 3
    assert celery_app.conf.task_track_started is True
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_send_sent_event is True
    assert celery_app.conf.worker_send_task_events is True
    assert celery_app.conf.task_time_limit == 900


def test_exhausted_task_retries_are_recorded_in_dead_letter_queue():
    previous_eager_setting = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    try:
        with (
            patch(
                "brasaland_api.modules.rfp_intake.router.process_rfp_draft_ticket",
                side_effect=RuntimeError("model unavailable"),
            ) as process,
            patch("brasaland_api.modules.task_storage.record_dead_letter") as record_dead_letter,
            patch("brasaland_api.modules.rfp_intake.storage.update_ticket") as update_ticket,
        ):
            result = generate_rfp_draft_task.apply(
                args=["ticket-1"],
                task_id="task-1",
                throw=False,
            )
    finally:
        celery_app.conf.task_always_eager = previous_eager_setting

    assert result.failed()
    assert process.call_count == 4
    record_dead_letter.assert_called_once_with(
        "task-1",
        "brasaland.generate_rfp_draft",
        4,
        "model unavailable",
    )
    assert update_ticket.call_args.args[1]["status"] == "needs_human_review"