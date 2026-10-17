"""Normalize Part 1 field labels for the Part 2 drafting/evaluation graph."""

from __future__ import annotations

import re
from typing import Any, Callable

from .drafting import run_rfp_draft_generation as _run_rfp_draft_generation

_QUESTION_LABELS = {
    "budget_range": "presupuesto / budget range",
    "deadline": "fecha límite / deadline",
    "client_name": "nombre del cliente / client name",
    "location": "ubicación / location",
    "scope": "alcance / scope",
}


async def run_rfp_draft_generation(
    *,
    ticket_id: str,
    metadata: dict[str, Any],
    handoff_payload: dict[str, Any],
    department_sections: list[dict[str, Any]],
    status_callback: Callable[[str], None] | None = None,
    progress_callback: Callable[[list[dict[str, Any]], dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Pass a presentation copy to the graph without changing persisted source fields."""
    normalized_sections = []
    for original in department_sections:
        section = dict(original)
        aspects = dict(section.get("key_aspects") or {})
        open_questions = []
        for question in aspects.get("open_questions") or []:
            value = str(question)
            label = _QUESTION_LABELS.get(value.casefold())
            open_questions.append(f"{value} ({label})" if label else value)
        aspects["open_questions"] = open_questions
        section["key_aspects"] = aspects
        normalized_sections.append(section)

    normalized_metadata = dict(metadata)
    budget_range = normalized_metadata.get("budget_range")
    if isinstance(budget_range, str):
        normalized_metadata["budget_range"] = re.sub(r"\bUS\$", "USD", budget_range, flags=re.I)

    return await _run_rfp_draft_generation(
        ticket_id=ticket_id,
        metadata=normalized_metadata,
        handoff_payload=handoff_payload,
        department_sections=normalized_sections,
        status_callback=status_callback,
        progress_callback=progress_callback,
    )