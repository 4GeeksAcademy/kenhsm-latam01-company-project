"""PostgREST persistence for RFP tickets, metadata, and department sections."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from brasaland_api.core.config import Settings, get_settings


class RFPStorageError(RuntimeError):
    """Supabase is unavailable or rejected an RFP persistence operation."""


def _request(
    method: str,
    table: str,
    *,
    params: dict[str, str] | None = None,
    payload: Any = None,
    prefer: str | None = None,
    settings: Settings | None = None,
) -> Any:
    settings = settings or get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RFPStorageError("Supabase storage is not configured")

    secret = settings.supabase_service_role_key.get_secret_value()
    headers = {
        "apikey": secret,
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
        "Accept-Profile": "public",
        "Content-Profile": "public",
    }
    if prefer:
        headers["Prefer"] = prefer
    try:
        response = httpx.request(
            method,
            f"{settings.supabase_url.rstrip('/')}/rest/v1/{table}",
            params=params,
            json=payload,
            headers=headers,
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json() if response.content else None
    except httpx.HTTPError as error:
        raise RFPStorageError(f"Supabase RFP storage failed for {table}") from error


def create_ticket(ticket: dict[str, Any]) -> None:
    _request("POST", "rfp_tickets", payload=ticket, prefer="return=minimal")


def update_ticket(ticket_id: str, values: dict[str, Any]) -> None:
    _request(
        "PATCH",
        "rfp_tickets",
        params={"ticket_id": f"eq.{ticket_id}"},
        payload=values,
        prefer="return=minimal",
    )


def claim_draft_generation(ticket_id: str, expected_status: str = "analisis_completo") -> bool:
    """Atomically claim a completed Part 1 ticket or an explicitly reopened review."""
    if expected_status not in {"analisis_completo", "needs_human_review"}:
        return False
    rows = _request(
        "PATCH",
        "rfp_tickets",
        params={"ticket_id": f"eq.{ticket_id}", "status": f"eq.{expected_status}"},
        payload={"status": "generando_borrador", "updated_at": datetime.now(timezone.utc).isoformat()},
        prefer="return=representation",
    )
    return bool(rows)


def persist_analysis(
    ticket_id: str,
    metadata: dict[str, Any],
    department_sections: list[dict[str, Any]],
) -> None:
    metadata_row = {"ticket_id": ticket_id, **metadata}
    _request(
        "POST",
        "rfp_metadata",
        payload=metadata_row,
        prefer="resolution=merge-duplicates,return=minimal",
    )
    section_rows = [
        {
            "ticket_id": ticket_id,
            "department_id": section["department_id"],
            "key_aspects": {
                **section["key_aspects"],
                "department_name": section["department_name"],
                "contact": section["contact"],
            },
        }
        for section in department_sections
    ]
    if section_rows:
        _request(
            "POST",
            "department_sections",
            payload=section_rows,
            prefer="resolution=merge-duplicates,return=minimal",
        )


def persist_draft_sections(ticket_id: str, sections: list[dict[str, Any]]) -> None:
    for section in sections:
        rows = _request(
            "PATCH",
            "department_sections",
            params={
                "ticket_id": f"eq.{ticket_id}",
                "department_id": f"eq.{section['department_id']}",
            },
            payload={
                "draft_content": section.get("draft_content"),
                "evaluation_results": section.get("evaluation_results"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            prefer="return=representation",
        )
        if not rows:
            raise RFPStorageError("Part 1 department section is missing during draft persistence")


def update_draft_section(ticket_id: str, section: dict[str, Any]) -> None:
    rows = _request(
        "PATCH",
        "department_sections",
        params={
            "ticket_id": f"eq.{ticket_id}",
            "department_id": f"eq.{section['department_id']}",
        },
        payload={
            "draft_content": section.get("draft_content"),
            "evaluation_results": section.get("evaluation_results"),
            "approval_status": section.get("approval_status", "pendiente"),
            "approver": section.get("approver"),
            "approved_at": section.get("approved_at"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        prefer="return=representation",
    )
    if not rows:
        raise RFPStorageError("Department section is missing during approval update")


def save_approval(ticket_id: str, approval_key: str, values: dict[str, Any]) -> None:
    _request(
        "POST",
        "rfp_human_approvals",
        params={"on_conflict": "ticket_id,approval_key"},
        payload={"ticket_id": ticket_id, "approval_key": approval_key, **values},
        prefer="resolution=merge-duplicates,return=minimal",
    )


def list_approvals(ticket_id: str) -> list[dict[str, Any]]:
    return _request(
        "GET",
        "rfp_human_approvals",
        params={"ticket_id": f"eq.{ticket_id}", "select": "*", "order": "approval_key.asc"},
    )


def persist_execution_events(ticket_id: str, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    rows = [{"ticket_id": ticket_id, **event} for event in events]
    _request(
        "POST",
        "rfp_execution_events",
        params={"on_conflict": "event_id"},
        payload=rows,
        prefer="resolution=ignore-duplicates,return=minimal",
    )


def persist_final_document(document: dict[str, Any]) -> None:
    _request(
        "POST",
        "rfp_final_documents",
        params={"on_conflict": "ticket_id"},
        payload=document,
        prefer="resolution=merge-duplicates,return=minimal",
    )


def get_final_document(ticket_id: str) -> dict[str, Any] | None:
    rows = _request(
        "GET",
        "rfp_final_documents",
        params={"ticket_id": f"eq.{ticket_id}", "select": "*", "limit": "1"},
    )
    return rows[0] if rows else None


def get_ticket(ticket_id: str) -> dict[str, Any] | None:
    rows = _request(
        "GET",
        "rfp_tickets",
        params={"ticket_id": f"eq.{ticket_id}", "select": "*", "limit": "1"},
    )
    if not rows:
        return None
    ticket = rows[0]
    metadata = _request(
        "GET",
        "rfp_metadata",
        params={"ticket_id": f"eq.{ticket_id}", "select": "*", "limit": "1"},
    )
    sections = _request(
        "GET",
        "department_sections",
        params={"ticket_id": f"eq.{ticket_id}", "select": "*", "order": "department_id.asc"},
    )
    approvals = list_approvals(ticket_id)
    events = _request(
        "GET",
        "rfp_execution_events",
        params={"ticket_id": f"eq.{ticket_id}", "select": "event_id,agent,input,output,timestamp", "order": "timestamp.asc"},
    )
    ticket["metadata"] = metadata[0] if metadata else None
    ticket["department_sections"] = sections
    ticket["approvals"] = approvals
    ticket["execution_trace"] = events
    ticket["final_document"] = get_final_document(ticket_id)
    return ticket


def list_tickets(limit: int = 50) -> list[dict[str, Any]]:
    return _request(
        "GET",
        "rfp_tickets",
        params={"select": "ticket_id,rfp_id,status,raw_pdf_path,processing_error,created_at,updated_at", "order": "created_at.desc", "limit": str(limit)},
    )