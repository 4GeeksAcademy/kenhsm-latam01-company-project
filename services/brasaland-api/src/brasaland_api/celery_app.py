"""Celery application and independently executed RFP draft task."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from celery import Celery

from brasaland_api.core.config import get_settings

logger = logging.getLogger("brasaland.tasks")
redis_url = get_settings().redis_url
celery_app = Celery("brasaland", broker=redis_url, backend=redis_url)
celery_app.conf.update(
    accept_content=["json"],
    result_serializer="json",
    task_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    task_time_limit=900,
    task_soft_time_limit=840,
    worker_prefetch_multiplier=1,
    result_expires=86400,
)


@celery_app.task(
    bind=True,
    name="brasaland.generate_rfp_draft",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_rfp_draft_task(self, ticket_id: str) -> dict[str, str]:
    started = time.monotonic()
    attempt = self.request.retries + 1
    task_id = self.request.id or "unknown"
    logger.info("task_id=%s task=generate_rfp_draft attempt=%s status=started", task_id, attempt)

    try:
        from brasaland_api.modules.rfp_intake.router import process_rfp_draft_ticket

        process_rfp_draft_ticket(ticket_id)
    except Exception as error:
        duration = time.monotonic() - started
        if self.request.retries < self.max_retries:
            countdown = 2 ** (self.request.retries + 1)
            logger.warning(
                "task_id=%s task=generate_rfp_draft attempt=%s status=retry duration_seconds=%.3f countdown_seconds=%s error=%s",
                task_id,
                attempt,
                duration,
                countdown,
                error,
            )
            raise self.retry(exc=error, countdown=countdown)

        from brasaland_api.modules.rfp_intake import storage as rfp_storage
        from brasaland_api.modules.task_storage import record_dead_letter

        try:
            record_dead_letter(task_id, "brasaland.generate_rfp_draft", attempt, str(error))
        except Exception:
            logger.exception("task_id=%s attempt=%s status=dlq_persist_failed", task_id, attempt)
        try:
            rfp_storage.update_ticket(
                ticket_id,
                {
                    "status": "needs_human_review",
                    "processing_error": str(error)[:2000],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception:
            logger.exception("task_id=%s attempt=%s status=ticket_failure_update_failed", task_id, attempt)
        logger.exception(
            "task_id=%s task=generate_rfp_draft attempt=%s status=failure duration_seconds=%.3f error=%s",
            task_id,
            attempt,
            duration,
            error,
        )
        raise

    duration = time.monotonic() - started
    logger.info(
        "task_id=%s task=generate_rfp_draft attempt=%s status=success duration_seconds=%.3f",
        task_id,
        attempt,
        duration,
    )
    return {"ticket_id": ticket_id}