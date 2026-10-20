"""Checkpointed human approval branches and deterministic RFP arbitration."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from operator import add
from pathlib import Path
from typing import Annotated, Any, TypedDict
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

DEPARTMENT_APPROVERS = {
    "marketing": "Camila Ospina",
    "operaciones": "Felipe Guerrero",
    "procurement": "Lucía Fernández",
    "training": "Jake Morrison",
}
CEO_APPROVER = "Mariana Restrepo"
CEO_APPROVAL_THRESHOLD_USD = 50_000
MAX_APPROVAL_CHANGE_ITERATIONS = 3
APPROVAL_ACTIONS = {"approve", "reject", "request_changes"}


class ApprovalState(TypedDict, total=False):
    ticket_id: str
    approval_key: str
    approver: str
    metadata: dict[str, Any]
    section: dict[str, Any]
    all_sections: list[dict[str, Any]]
    handoff_payload: dict[str, Any]
    conflicts: list[dict[str, Any]]
    branch_conflicts: list[dict[str, Any]]
    approval_request: dict[str, Any]
    human_response: dict[str, Any]
    decision: dict[str, Any]
    trace: Annotated[list[dict[str, Any]], add]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trace(agent: str, input_value: Any, output_value: Any) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "agent": agent,
        "input": input_value,
        "output": output_value,
        "timestamp": _timestamp(),
    }


def _numeric(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _annual_usd_estimate(metadata: dict[str, Any], handoff: dict[str, Any]) -> float | None:
    for source in (metadata, handoff):
        for key in ("annual_estimated_value_usd", "estimated_annual_value_usd", "total_estimated_value_usd"):
            amount = _numeric(source.get(key))
            if amount is not None:
                return amount

    budget = str(metadata.get("budget_range") or "")
    scope = " ".join(str(item) for item in (metadata.get("scope") or []))
    combined = f"{budget} {scope}"
    if not re.search(r"\b(?:USD|US\$)\b", combined, re.I):
        return None
    if not re.search(r"annual|anual|per\s+year|por\s+a[nñ]o|/\s*a[nñ]o|12\s+months|12\s+meses|1\s+year|1\s+a[nñ]o", combined, re.I):
        return None
    values = [float(value.replace(",", "")) for value in re.findall(r"\b\d[\d,]*(?:\.\d+)?\b", budget)]
    return max(values) if values else None


def _section_terms(section: dict[str, Any]) -> dict[str, Any]:
    evaluation = section.get("evaluation_results") or {}
    return {
        **(section.get("commercial_terms") or {}),
        **(evaluation.get("commercial_terms") or {}),
    }


def detect_approval_conflicts(
    metadata: dict[str, Any],
    sections: list[dict[str, Any]],
    handoff_payload: dict[str, Any],
    approvals: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Detect only conflicts represented by structured fields or evaluator output."""
    by_department = {section.get("department_id"): section for section in sections}
    conflicts: list[dict[str, Any]] = []

    operations_terms = _section_terms(by_department.get("operaciones", {}))
    procurement_terms = _section_terms(by_department.get("procurement", {}))
    quoted_price = _numeric(operations_terms.get("price_per_event_usd"))
    estimated_cost = _numeric(procurement_terms.get("cost_per_event_usd"))
    if quoted_price is not None and estimated_cost is not None and quoted_price < estimated_cost:
        conflicts.append({
            "trigger_id": "cost-vs-feasibility",
            "owner": DEPARTMENT_APPROVERS["marketing"],
            "departments": ["operaciones", "procurement"],
            "resolution": "request_changes: subir precio o reducir alcance antes del sign-off.",
            "structured_values": {
                "price_per_event_usd": quoted_price,
                "cost_per_event_usd": estimated_cost,
            },
        })

    sla_departments = []
    for department_id, section in by_department.items():
        terms = _section_terms(section)
        lead_days = _numeric(terms.get("setup_lead_time_business_days"))
        evaluation = section.get("evaluation_results") or {}
        compliance = evaluation.get("compliance") or {}
        violations = compliance.get("violations") or []
        short_sla = lead_days is not None and lead_days < 10
        evaluator_flag = any("menos de 10 días hábiles" in str(item).casefold() for item in violations)
        if short_sla or evaluator_flag:
            sla_departments.append(department_id)
    if sla_departments:
        owner = DEPARTMENT_APPROVERS["operaciones"] if sla_departments == ["operaciones"] else DEPARTMENT_APPROVERS["marketing"]
        conflicts.append({
            "trigger_id": "setup-sla-breach",
            "owner": owner,
            "departments": sorted(sla_departments),
            "resolution": "request_changes: corregir todas las promesas de montaje/entrega a un mínimo de 10 días hábiles.",
            "escalation": "Felipe Guerrero rechaza; Camila Ospina escala si otra área mantiene la promesa." if owner == DEPARTMENT_APPROVERS["marketing"] else None,
        })

    annual_usd = _annual_usd_estimate(metadata, handoff_payload)
    ceo_status = (approvals or {}).get("ceo", {}).get("approval_status")
    if annual_usd is not None and annual_usd > CEO_APPROVAL_THRESHOLD_USD and ceo_status != "aprobado":
        conflicts.append({
            "trigger_id": "ceo-threshold",
            "owner": CEO_APPROVER,
            "departments": [],
            "resolution": "bloquear ultimate synthesizer hasta approve de CEO; un rechazo bloquea el cierre.",
            "structured_values": {"annual_estimated_value_usd": annual_usd},
        })
    return conflicts


def validate_human_response(response: Any, conflicts: list[dict[str, Any]] | None = None) -> dict[str, str]:
    if not isinstance(response, dict):
        raise ValueError("La respuesta de aprobación debe ser un objeto.")
    action = response.get("action")
    comment = str(response.get("comment") or "").strip()
    if action not in APPROVAL_ACTIONS:
        raise ValueError("La acción debe ser approve, reject o request_changes.")
    if action == "request_changes" and not comment:
        raise ValueError("request_changes requiere indicar los cambios solicitados.")
    if action == "approve" and conflicts:
        raise ValueError("No se puede aprobar mientras haya conflictos de arbitraje sin resolver.")
    return {"action": action, "comment": comment}


def can_request_changes(iteration_count: int) -> bool:
    return iteration_count < MAX_APPROVAL_CHANGE_ITERATIONS


def _prepare_approval(state: ApprovalState) -> dict[str, Any]:
    section = state.get("section") or {}
    approval_request = {
        "ticket_id": state["ticket_id"],
        "approval_key": state["approval_key"],
        "approver": state["approver"],
        "client_name": (state.get("metadata") or {}).get("client_name"),
        "draft_content": section.get("draft_content"),
        "evaluation_results": section.get("evaluation_results"),
        "conflicts": state.get("branch_conflicts", []),
        "actions": ["approve", "reject", "request_changes"],
    }
    return {
        "approval_request": approval_request,
        "trace": [_trace("approval_request_builder", {"ticket_id": state["ticket_id"], "approval_key": state["approval_key"]}, approval_request)],
    }


def _arbitrate(state: ApprovalState) -> dict[str, Any]:
    approval_key = state["approval_key"]
    relevant = [
        conflict for conflict in state.get("conflicts", [])
        if (approval_key == "ceo" and conflict["trigger_id"] == "ceo-threshold")
        or approval_key in conflict.get("departments", [])
    ]
    result = {"approval_key": approval_key, "triggers": [item["trigger_id"] for item in relevant]}
    return {
        "branch_conflicts": relevant,
        "trace": [_trace("fixed_arbitrator", {"approval_key": approval_key, "conflicts": relevant}, result)],
    }


def _human_approval(state: ApprovalState) -> dict[str, Any]:
    response = interrupt(state["approval_request"])
    return {"human_response": response}


def _validate_decision(state: ApprovalState) -> dict[str, Any]:
    response = validate_human_response(state.get("human_response"), state.get("branch_conflicts"))
    output = {"approval_key": state["approval_key"], **response}
    return {
        "decision": output,
        "trace": [_trace("approval_response_validator", state.get("human_response"), output)],
    }


def build_approval_graph():
    graph = StateGraph(ApprovalState)
    graph.add_node("prepare_approval", _prepare_approval)
    graph.add_node("fixed_arbitrator", _arbitrate)
    graph.add_node("human_approval", _human_approval)
    graph.add_node("validate_decision", _validate_decision)
    graph.add_edge(START, "prepare_approval")
    graph.add_edge("prepare_approval", "fixed_arbitrator")
    graph.add_edge("fixed_arbitrator", "human_approval")
    graph.add_edge("human_approval", "validate_decision")
    graph.add_edge("validate_decision", END)
    return graph


def approval_thread_id(ticket_id: str, approval_key: str, revision: int = 1) -> str:
    return f"rfp-{ticket_id}:{approval_key}:revision-{revision}"


def invoke_approval_branch(
    *,
    checkpoint_path: str,
    ticket_id: str,
    approval_key: str,
    revision: int = 1,
    initial_state: dict[str, Any] | None = None,
    response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Start or resume exactly one approval branch using its durable checkpoint."""
    path = Path(checkpoint_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(path)) as checkpointer:
        checkpointer.setup()
        graph = build_approval_graph().compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": approval_thread_id(ticket_id, approval_key, revision)}}
        graph_input: Any
        if response is None:
            if initial_state is None:
                raise ValueError("initial_state es obligatorio al iniciar la rama.")
            graph_input = initial_state
        else:
            graph_input = Command(resume=validate_human_response(response))
        result = graph.invoke(graph_input, config=config)

    paused = bool(result.get("__interrupt__"))
    trace = list(result.get("trace", []))
    if paused:
        interrupt_payload = result["__interrupt__"][0].value
        trace.append(_trace("human_approval_interrupt", interrupt_payload, {"status": "paused"}))
    return {"paused": paused, "state": result, "decision": result.get("decision"), "trace": trace}