"""Runnable LangGraph entry point with parallel department worker aggregation."""

from __future__ import annotations

import re
from operator import add
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .graph import (
    _extract_relevant_excerpt,
    _synthesize,
    route_departments,
    run_department_worker,
)
from .intake import extract_rfp_metadata


class IntakeState(TypedDict, total=False):
    ticket_id: str
    markdown: str
    classification: dict[str, Any]
    metadata: dict[str, Any]
    departments_needed: list[str]
    department_results: Annotated[list[dict[str, Any]], add]
    handoff_payload: dict[str, Any]


def classify_rfp(markdown: str) -> dict[str, Any]:
    text = markdown.casefold()
    service = any(term in text for term in (
        "catering", "concesion", "concesión", "co-brand", "co brand", "restaurante",
        "food service", "alimentación", "alimentacion", "propuesta", "cotización", "cotizacion",
        "rfp", "request for proposal",
    ))
    scope = any(term in text for term in (
        "comensales", "empleados", "resorts", "ubicaciones", "semanal", "mensual", "meses",
        "anual", "eventos", "volumen", "menú", "menu", "servicio",
    )) or bool(re.search(r"\b\d[\d,.]*\b", text))
    request = any(term in text for term in (
        "solicit", "request", "propon", "proposal", "cotiz", "quote", "busc", "interes",
        "necesit", "requer", "invite",
    ))
    commitment = any(term in text for term in (
        "deadline", "fecha límite", "fecha limite", "antes del", "presupuesto", "budget",
        "contrato", "meses", "anual", "annual",
    ))
    accepted = service and scope and request and commitment
    return {
        "is_valid": accepted,
        "reason": "Solicitud accionable de propuesta con servicio, alcance y compromiso identificables." if accepted else "No se identificó una solicitud accionable con servicio, alcance y compromiso suficientes.",
    }


def _classify_node(state: IntakeState) -> dict[str, Any]:
    return {"classification": classify_rfp(state.get("markdown", ""))}


def _route_classification(state: IntakeState) -> str:
    return "metadata" if state.get("classification", {}).get("is_valid") else END


def _metadata_node(state: IntakeState) -> dict[str, Any]:
    markdown = state.get("markdown", "")
    metadata = extract_rfp_metadata(markdown)
    departments = route_departments(markdown)
    metadata["departments_needed"] = departments
    return {"metadata": metadata, "departments_needed": departments}


def _dispatch_workers(state: IntakeState) -> list[Send]:
    markdown = state.get("markdown", "")
    return [
        Send("department_worker", {
            "department_id": department_id,
            "metadata": state.get("metadata", {}),
            "excerpt": _extract_relevant_excerpt(markdown, department_id),
        })
        for department_id in state.get("departments_needed", [])
    ]


def _worker_node(state: dict[str, Any]) -> dict[str, Any]:
    return {"department_results": [run_department_worker(state)]}


def _synthesizer_node(state: IntakeState) -> dict[str, Any]:
    state_for_synthesis = dict(state)
    return _synthesize(state_for_synthesis)


def build_rfp_intake_graph():
    graph = StateGraph(IntakeState)
    graph.add_node("classifier", _classify_node)
    graph.add_node("metadata", _metadata_node)
    graph.add_node("department_worker", _worker_node)
    graph.add_node("synthesizer", _synthesizer_node)
    graph.add_edge(START, "classifier")
    graph.add_conditional_edges("classifier", _route_classification, {"metadata": "metadata", END: END})
    graph.add_conditional_edges("metadata", _dispatch_workers, ["department_worker"])
    graph.add_edge("department_worker", "synthesizer")
    graph.add_edge("synthesizer", END)
    return graph.compile()


rfp_intake_graph = build_rfp_intake_graph()