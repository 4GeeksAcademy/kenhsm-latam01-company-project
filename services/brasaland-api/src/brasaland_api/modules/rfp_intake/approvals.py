"""Persistence orchestration for independent RFP approval branches."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from brasaland_api.core.config import get_settings
from brasaland_api.modules.rfp_intake import storage
from data.pipelines.rfp_intake.approval import (
    CEO_APPROVER,
    DEPARTMENT_APPROVERS,
    MAX_APPROVAL_CHANGE_ITERATIONS,
    can_request_changes,
    detect_approval_conflicts,
    invoke_approval_branch,
    validate_human_response,
    _annual_usd_estimate as get_annual_usd_estimate,
)
from data.pipelines.rfp_intake.drafting import evaluate_section, generate_department_draft


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event(agent: str, input_value: Any, output_value: Any) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "agent": agent,
        "input": input_value,
        "output": output_value,
        "timestamp": _now(),
    }


def _approval_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["approval_key"]: row for row in rows}


def _checkpoint_path() -> str:
    return get_settings().rfp_checkpoint_path


def _department_conflicts(conflicts: list[dict[str, Any]], approval_key: str) -> list[dict[str, Any]]:
    if approval_key == "ceo":
        return []
    return [conflict for conflict in conflicts if approval_key in conflict.get("departments", [])]


def _start_branch(
    ticket: dict[str, Any],
    approval_key: str,
    revision: int,
    conflicts: list[dict[str, Any]],
) -> dict[str, Any]:
    sections = ticket.get("department_sections") or []
    section = next((item for item in sections if item.get("department_id") == approval_key), {})
    approver = CEO_APPROVER if approval_key == "ceo" else DEPARTMENT_APPROVERS[approval_key]
    branch_conflicts = _department_conflicts(conflicts, approval_key)
    initial = {
        "ticket_id": ticket["ticket_id"],
        "approval_key": approval_key,
        "approver": approver,
        "metadata": ticket.get("metadata") or {},
        "section": section,
        "all_sections": sections,
        "handoff_payload": ticket.get("handoff_payload") or {},
        "conflicts": branch_conflicts,
    }
    result = invoke_approval_branch(
        checkpoint_path=_checkpoint_path(),
        ticket_id=ticket["ticket_id"],
        approval_key=approval_key,
        revision=revision,
        initial_state=initial,
    )
    storage.persist_execution_events(ticket["ticket_id"], result["trace"])
    if approval_key == "ceo":
        storage.persist_execution_events(ticket["ticket_id"], [
            _event("fixed_arbitrator", conflicts, {"trigger_id": "ceo-threshold", "owner": CEO_APPROVER, "blocks_synthesizer": True})
            for conflict in conflicts if conflict["trigger_id"] == "ceo-threshold"
        ])
    storage.save_approval(ticket["ticket_id"], approval_key, {
        "approval_status": "pendiente",
        "approver": approver,
        "comment": None,
        "revision": revision,
        "approved_at": None,
        "updated_at": _now(),
    })
    if approval_key != "ceo":
        section["approval_status"] = "pendiente"
        section["approver"] = None
        section["approved_at"] = None
        storage.update_draft_section(ticket["ticket_id"], section)
    return result


def initialize_approval_branches(ticket: dict[str, Any]) -> None:
    sections = ticket.get("department_sections") or []
    metadata = ticket.get("metadata") or {}
    handoff = ticket.get("handoff_payload") or {}
    conflicts = detect_approval_conflicts(metadata, sections, handoff)
    departments = metadata.get("departments_needed") or handoff.get("departments_needed") or [
        section["department_id"] for section in sections
    ]
    ceo_required = any(conflict["trigger_id"] == "ceo-threshold" for conflict in conflicts)
    for approval_key in departments:
        revision = 1
        _start_branch(ticket, approval_key, revision, conflicts)
    if ceo_required:
        _start_branch(ticket, "ceo", 1, conflicts)
        handoff["required_approvals"] = sorted(set(handoff.get("required_approvals") or []) | {CEO_APPROVER})
    required_approvals = list(departments)
    if ceo_required:
        required_approvals.append("ceo")
    handoff["approval_workflow"] = {
        "status": "waiting_for_signoff",
        "max_change_iterations": MAX_APPROVAL_CHANGE_ITERATIONS,
        "departments": departments,
        "required_approvals": required_approvals,
        "conflicts": conflicts,
    }
    storage.update_ticket(ticket["ticket_id"], {
        "status": "esperando_aprobación",
        "handoff_payload": handoff,
        "updated_at": _now(),
    })


def _record_decision(ticket_id: str, approval_key: str, approver: str, decision: dict[str, Any], revision: int) -> None:
    action = decision["action"]
    storage.save_approval(ticket_id, approval_key, {
        "approval_status": {"approve": "aprobado", "reject": "rechazado", "request_changes": "cambios_solicitados"}[action],
        "approver": approver,
        "comment": decision.get("comment") or None,
        "revision": revision,
        "approved_at": _now() if action == "approve" else None,
        "updated_at": _now(),
    })
    if approval_key != "ceo":
        ticket = storage.get_ticket(ticket_id)
        section = next(item for item in ticket["department_sections"] if item["department_id"] == approval_key)
        section["approval_status"] = "aprobado" if action == "approve" else "rechazado"
        section["approver"] = approver
        section["approved_at"] = _now() if action == "approve" else None
        storage.update_draft_section(ticket_id, section)


def _section_iteration_count(handoff: dict[str, Any], department_id: str) -> int:
    for section in (handoff.get("draft_generation") or {}).get("sections", []):
        if section.get("department_id") == department_id:
            return int(section.get("iteration_count") or 0)
    return 0


def _regenerate_section(ticket: dict[str, Any], department_id: str, feedback: str, approval_revision: int) -> dict[str, Any]:
    metadata = ticket.get("metadata") or {}
    section = next(item for item in ticket.get("department_sections", []) if item["department_id"] == department_id)
    previous_evaluation = section.get("evaluation_results") or {}
    previous_feedback = str(previous_evaluation.get("feedback_for_generator") or "")
    combined_feedback = " ".join(part for part in (previous_feedback, feedback) if part)
    draft = generate_department_draft(
        department_id,
        metadata,
        section.get("key_aspects") or {},
        previous_draft=str(section.get("draft_content") or ""),
        feedback=combined_feedback,
    )
    evaluation = asyncio.run(evaluate_section(draft, metadata, section.get("key_aspects") or {}))
    updated = {
        **section,
        "draft_content": draft,
        "evaluation_results": {
            **evaluation,
            "commercial_terms": previous_evaluation.get("commercial_terms", {}),
            "human_change_request": feedback,
        },
        "approval_status": "pendiente",
        "approver": None,
        "approved_at": None,
    }
    handoff = dict(ticket.get("handoff_payload") or {})
    draft_generation = dict(handoff.get("draft_generation") or {})
    summaries = [dict(item) for item in draft_generation.get("sections", [])]
    summary = {
        "department_id": department_id,
        "draft_content": draft,
        "evaluation_results": updated["evaluation_results"],
        "iteration_count": _section_iteration_count(handoff, department_id) + 1,
        "section_status": "needs_human_review" if not evaluation["overall_pass"] else "ready_for_part_3",
    }
    summaries = [item for item in summaries if item.get("department_id") != department_id]
    summaries.append(summary)
    draft_generation["sections"] = sorted(summaries, key=lambda item: item["department_id"])
    draft_generation["status"] = "needs_human_review" if any(not item.get("evaluation_results", {}).get("overall_pass", False) for item in summaries) else "ready_for_part_3"
    handoff["draft_generation"] = draft_generation
    handoff.setdefault("approval_change_iterations", {})[department_id] = approval_revision
    handoff.setdefault("approval_feedback", []).append({
        "approval_key": department_id,
        "comment": feedback,
        "timestamp": _now(),
    })
    updated["iteration_count"] = summary["iteration_count"]
    storage.update_draft_section(ticket["ticket_id"], updated)
    storage.update_ticket(ticket["ticket_id"], {"handoff_payload": handoff, "updated_at": _now()})
    ticket["handoff_payload"] = handoff
    ticket["department_sections"] = [updated if item["department_id"] == department_id else item for item in ticket["department_sections"]]
    storage.persist_execution_events(ticket["ticket_id"], [
        _event("department_generator", {"department_id": department_id, "feedback": feedback}, {"draft_content": draft, "evaluation_results": updated["evaluation_results"]})
    ])
    return updated


def _document_markdown(ticket: dict[str, Any], sections: list[dict[str, Any]], generated_at: str, total_value: float | None) -> str:
    metadata = ticket.get("metadata") or {}
    client = metadata.get("client_name") or "Cliente"
    parts = [f"# Propuesta Brasaland para {client}", "", f"Emitida: {generated_at[:10]}"]
    for label, key in (("Ubicación", "location"), ("Servicio", "service_type"), ("Alcance", "scope"), ("Fecha límite", "deadline")):
        value = metadata.get(key)
        if value:
            rendered = "; ".join(map(str, value)) if isinstance(value, list) else str(value)
            parts.append(f"**{label}:** {rendered}")
    if total_value is not None:
        parts.extend(["", f"**Valor anual estimado:** USD {total_value:,.2f}"])
    for section in sections:
        aspects = section.get("key_aspects") or {}
        parts.extend(["", f"## {section.get('department_name') or aspects.get('department_name') or section['department_id']}", "", str(section.get("draft_content") or "")])
    joined = "\n".join(parts)
    if not any(marker in joined.casefold() for marker in ("30 días", "30 dias", "30 days")):
        joined += "\n\nLa oferta tiene validez de 30 días desde su emisión."
    return joined


def reconcile_approval_status(ticket_id: str) -> str:
    ticket = storage.get_ticket(ticket_id)
    if ticket is None:
        raise storage.RFPStorageError("RFP ticket not found during approval reconciliation")
    sections = ticket.get("department_sections") or []
    metadata = ticket.get("metadata") or {}
    handoff = ticket.get("handoff_payload") or {}
    records = storage.list_approvals(ticket_id)
    approvals = _approval_map(records)
    departments = metadata.get("departments_needed") or handoff.get("departments_needed") or [item["department_id"] for item in sections]
    required = list(departments)
    if "Mariana Restrepo" in (handoff.get("required_approvals") or []):
        required.append("ceo")
    unresolved = [approvals.get(key, {}).get("approval_status") != "aprobado" for key in required]
    rejected = any(approvals.get(key, {}).get("approval_status") == "rechazado" for key in required)
    conflicts = detect_approval_conflicts(metadata, sections, handoff, approvals)
    workflow = dict(handoff.get("approval_workflow") or {})
    workflow["conflicts"] = conflicts
    handoff["approval_workflow"] = workflow
    if rejected:
        next_status = "needs_human_review"
    elif any(unresolved):
        next_status = "esperando_aprobación"
    else:
        blocking = [item for item in conflicts if item["trigger_id"] != "ceo-threshold"]
        if blocking:
            storage.persist_execution_events(ticket_id, [
                _event("fixed_arbitrator", blocking, {"result": "request_changes_required"})
            ])
            next_status = "needs_human_review"
        else:
            generated_at = _now()
            approved_sections = [
                {
                    "department_id": item["department_id"],
                    "department_name": (item.get("key_aspects") or {}).get("department_name", item["department_id"]),
                    "draft_content": item.get("draft_content"),
                    "approver": item.get("approver"),
                    "approved_at": item.get("approved_at"),
                }
                for item in sections if item.get("approval_status") == "aprobado"
            ]
            estimate = _annual_usd_estimate(metadata, handoff)
            document = {
                "ticket_id": ticket_id,
                "document_markdown": _document_markdown(ticket, approved_sections, generated_at, estimate),
                "sections": approved_sections,
                "total_estimated_value": estimate,
                "currency": "USD",
                "generated_at": generated_at,
            }
            storage.persist_final_document(document)
            storage.persist_execution_events(ticket_id, [
                _event("ultimate_document_synthesizer", {"approved_departments": [item["department_id"] for item in approved_sections]}, {"generated_at": generated_at, "section_count": len(approved_sections)})
            ])
            next_status = "terminado"
    handoff["approval_workflow"] = {**(handoff.get("approval_workflow") or {}), "status": next_status}
    storage.update_ticket(ticket_id, {"status": next_status, "handoff_payload": handoff, "updated_at": _now()})
    return next_status


def respond_to_approval(ticket_id: str, approval_key: str, approver_name: str, payload: dict[str, Any]) -> str:
    ticket = storage.get_ticket(ticket_id)
    if ticket is None:
        raise KeyError("Ticket RFP no encontrado.")
    handoff = ticket.get("handoff_payload") or {}
    approval_rows = storage.list_approvals(ticket_id)
    approvals = _approval_map(approval_rows)
    record = approvals.get(approval_key)
    if ticket.get("status") == "terminado" or not record or record.get("approval_status") != "pendiente":
        raise ValueError("Esta aprobación no está pendiente.")
    expected = CEO_APPROVER if approval_key == "ceo" else DEPARTMENT_APPROVERS.get(approval_key)
    if expected is None:
        raise ValueError("Departamento de aprobación desconocido.")
    if "ceo" != approval_key:
        active = (ticket.get("metadata") or {}).get("departments_needed") or handoff.get("departments_needed") or []
        if approval_key not in active:
            raise ValueError("El departamento no participa en esta RFP.")
    if " ".join(approver_name.casefold().split()) != " ".join(expected.casefold().split()):
        raise PermissionError(f"La aprobación corresponde a {expected}.")

    sections = ticket.get("department_sections") or []
    submitted_terms = {}
    if approval_key == "operaciones" and payload.get("price_per_event_usd") is not None:
        submitted_terms["price_per_event_usd"] = payload["price_per_event_usd"]
    if approval_key == "procurement" and payload.get("cost_per_event_usd") is not None:
        submitted_terms["cost_per_event_usd"] = payload["cost_per_event_usd"]
    if approval_key in DEPARTMENT_APPROVERS and payload.get("setup_lead_time_business_days") is not None:
        submitted_terms["setup_lead_time_business_days"] = payload["setup_lead_time_business_days"]
    if submitted_terms:
        section = next(item for item in sections if item["department_id"] == approval_key)
        evaluation = dict(section.get("evaluation_results") or {})
        evaluation["commercial_terms"] = {**evaluation.get("commercial_terms", {}), **submitted_terms}
        section["evaluation_results"] = evaluation
        storage.update_draft_section(ticket_id, section)
        ticket["department_sections"] = [section if item["department_id"] == approval_key else item for item in sections]
    conflicts = detect_approval_conflicts(ticket.get("metadata") or {}, sections, handoff, approvals)
    branch_conflicts = _department_conflicts(conflicts, approval_key)
    arbitration_event = _event(
        "fixed_arbitrator",
        {
            "approval_key": approval_key,
            "commercial_terms": submitted_terms,
            "detected_triggers": [item["trigger_id"] for item in conflicts],
        },
        {"conflicts": branch_conflicts, "action": "block_approve" if branch_conflicts else "continue"},
    )
    storage.persist_execution_events(ticket_id, [arbitration_event])
    if conflicts:
        handoff["approval_workflow"] = {**(handoff.get("approval_workflow") or {}), "conflicts": conflicts}
        storage.update_ticket(ticket_id, {"handoff_payload": handoff, "updated_at": _now()})
    response = validate_human_response(payload, branch_conflicts)
    revision = int(record.get("revision") or 1)
    branch = invoke_approval_branch(
        checkpoint_path=_checkpoint_path(),
        ticket_id=ticket_id,
        approval_key=approval_key,
        revision=revision,
        response=response,
    )
    if branch.get("decision") is None:
        raise ValueError("No se encontró un checkpoint pendiente para reanudar.")
    decision = branch["decision"]
    storage.persist_execution_events(ticket_id, [
        *branch["trace"],
        _event(f"human_approver:{expected}", branch["state"].get("approval_request", {}), decision),
    ])
    _record_decision(ticket_id, approval_key, expected, decision, revision)

    if decision["action"] == "request_changes":
        counts = dict(handoff.get("approval_change_iterations") or {})
        target_department = approval_key if approval_key in DEPARTMENT_APPROVERS else "marketing"
        count = int(counts.get(target_department) or 0)
        if not can_request_changes(count):
            storage.save_approval(ticket_id, approval_key, {
                "approval_status": "rechazado", "approver": expected,
                "comment": "Se alcanzó el límite de iteraciones de cambios.", "revision": revision,
                "approved_at": None, "updated_at": _now(),
            })
            if approval_key != "ceo":
                section = next(item for item in sections if item["department_id"] == approval_key)
                section["approval_status"] = "rechazado"
                section["approver"] = expected
                section["approved_at"] = None
                storage.update_draft_section(ticket_id, section)
            storage.update_ticket(ticket_id, {"status": "needs_human_review", "updated_at": _now()})
            return "needs_human_review"
        updated = _regenerate_section(ticket, target_department, decision["comment"], count + 1)
        revision += 1
        refreshed = storage.get_ticket(ticket_id)
        updated_approvals = dict(approvals)
        if approval_key != "ceo" and approvals.get("ceo"):
            ceo_revision = int(approvals["ceo"].get("revision") or 1) + 1
            storage.save_approval(ticket_id, "ceo", {
                "approval_status": "pendiente", "approver": CEO_APPROVER,
                "comment": "El documento cambió después del sign-off ejecutivo.",
                "revision": ceo_revision, "approved_at": None, "updated_at": _now(),
            })
            updated_approvals["ceo"] = {"approval_key": "ceo", "approval_status": "pendiente", "revision": ceo_revision}
        new_conflicts = detect_approval_conflicts(
            refreshed.get("metadata") or {},
            refreshed.get("department_sections") or [],
            refreshed.get("handoff_payload") or {},
            updated_approvals,
        )
        _start_branch(refreshed, target_department, revision, new_conflicts)
        if approval_key == "ceo" or (approval_key != "ceo" and updated_approvals.get("ceo")):
            ceo_revision = int(updated_approvals.get("ceo", {}).get("revision") or revision)
            _start_branch(refreshed, "ceo", ceo_revision, new_conflicts)
        return reconcile_approval_status(ticket_id)

    return reconcile_approval_status(ticket_id)


def _annual_usd_estimate(metadata: dict[str, Any], handoff: dict[str, Any]) -> float | None:
    return get_annual_usd_estimate(metadata, handoff)
