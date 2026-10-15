"""Dedicated orchestrator-worker-synthesizer graph for RFP intake."""

from __future__ import annotations

import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

DEPARTMENTS: dict[str, dict[str, str]] = {
    "marketing": {
        "name": "Marketing y Experiencia Digital",
        "contact": "Camila Ospina",
        "focus": "marca, exclusividad, co-branding y validez de la oferta",
    },
    "operaciones": {
        "name": "Operaciones de Restaurante",
        "contact": "Felipe Guerrero",
        "focus": "capacidad, personal, montaje y costo operativo por evento",
    },
    "procurement": {
        "name": "Procurement y Proveedores",
        "contact": "Lucía Fernández",
        "focus": "insumos, volumen y tiempos de entrega de proveedores",
    },
    "training": {
        "name": "Training y Estándares de Calidad",
        "contact": "Jake Morrison",
        "focus": "recetas nuevas, desarrollo y certificación",
    },
}

_SERVICE_TERMS = (
    "catering", "concesion", "concesión", "co-brand", "co brand", "co-branding",
    "restaurant", "restaurante", "food service", "alimentacion", "alimentación",
    "proposal", "propuesta", "cotizacion", "cotización", "rfp", "request for proposal",
)
_SCOPE_TERMS = (
    "comensales", "empleados", "personas", "ubicaciones", "resorts", "sedes", "semanal",
    "mensual", "anual", "meses", "año", "ano", "eventos", "volumen", "menu", "menú",
    "concesion", "concesión", "franquicia", "servicio",
)
_ACTION_TERMS = (
    "solicit", "request", "propon", "proposal", "cotiz", "quote", "buscamos", "interes",
    "interés", "necesit", "requer", "invite", "invita",
)


class RFPState(TypedDict, total=False):
    ticket_id: str
    markdown: str
    classification: dict[str, Any]
    metadata: dict[str, Any]
    departments_needed: list[str]
    department_results: list[dict[str, Any]]
    handoff_payload: dict[str, Any]


def classify_rfp(markdown: str) -> dict[str, Any]:
    """Classify actionable Brasaland proposal requests, including informal emails."""
    text = markdown.casefold()
    has_service = any(term in text for term in _SERVICE_TERMS)
    has_scope = any(term in text for term in _SCOPE_TERMS) or bool(re.search(r"\b\d[\d.,]*\b", text))
    has_action = any(term in text for term in _ACTION_TERMS)
    has_commitment = any(term in text for term in ("deadline", "fecha límite", "fecha limite", "antes del", "para el", "presupuesto", "budget", "contrato", "12 meses", "un año", "1 año", "annual", "anual"))
    is_valid = has_service and has_scope and has_action and has_commitment
    return {
        "is_valid": is_valid,
        "reason": "Solicitud accionable de propuesta con servicio, alcance y compromiso identificables." if is_valid else "No se identificó una solicitud accionable con servicio, alcance y compromiso suficientes.",
    }


def _extract_relevant_excerpt(markdown: str, department_id: str) -> str:
    keywords = {
        "marketing": ("brand", "marca", "exclusive", "exclusiv", "co-brand", "validez", "validity"),
        "operaciones": ("capacity", "capacidad", "staff", "personal", "setup", "montaje", "event", "evento", "resort"),
        "procurement": ("volume", "volumen", "supply", "proveedor", "ingredients", "insumos", "delivery", "entrega", "budget", "presupuesto"),
        "training": ("recipe", "receta", "menu", "menú", "standard", "estándar", "certification", "certificación", "chef"),
    }[department_id]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n|(?<=[.!?])\s+", markdown) if part.strip()]
    matches = [paragraph for paragraph in paragraphs if any(word in paragraph.casefold() for word in keywords)]
    return "\n".join(matches[:8])


def run_department_worker(state: dict[str, Any]) -> dict[str, Any]:
    """Create a bounded, extractive department brief without fabricating figures."""
    department_id = state["department_id"]
    metadata = state.get("metadata", {})
    excerpt = state.get("excerpt", "")
    open_questions = list(metadata.get("open_questions", []))
    return {
        "department_id": department_id,
        "department_name": DEPARTMENTS[department_id]["name"],
        "contact": DEPARTMENTS[department_id]["contact"],
        "key_aspects": {
            "focus": DEPARTMENTS[department_id]["focus"],
            "source_extracts": [excerpt] if excerpt else [],
            "open_questions": open_questions,
        },
    }


def _classify(state: RFPState) -> dict[str, Any]:
    return {"classification": classify_rfp(state.get("markdown", ""))}


def _route_classification(state: RFPState) -> str:
    return "extract_metadata" if state.get("classification", {}).get("is_valid") else END


def _extract_metadata(state: RFPState) -> dict[str, Any]:
    from .intake import extract_rfp_metadata

    metadata = extract_rfp_metadata(state.get("markdown", ""))
    departments = route_departments(state.get("markdown", ""))
    metadata["departments_needed"] = departments
    return {"metadata": metadata, "departments_needed": departments}


def route_departments(markdown: str) -> list[str]:
    text = markdown.casefold()
    active = ["marketing"]
    if any(word in text for word in ("catering", "comensales", "empleados", "resort", "evento", "concesion", "concesión", "capacidad")):
        active.append("operaciones")
    if any(word in text for word in ("volumen", "comensales", "empleados", "insumos", "presupuesto", "budget", "proveedor", "catering")):
        active.append("procurement")
    if any(word in text for word in ("co-brand", "co brand", "autor", "receta nueva", "menu nuevo", "menú nuevo", "custom menu", "chef")):
        active.append("training")
    return active


def _dispatch_workers(state: RFPState) -> list[Send]:
    return [
        Send(
            "department_worker",
            {
                "department_id": department_id,
                "metadata": state.get("metadata", {}),
                "excerpt": _extract_relevant_excerpt(state.get("markdown", ""), department_id),
            },
        )
        for department_id in state.get("departments_needed", [])
    ]


def _worker(state: dict[str, Any]) -> dict[str, Any]:
    return {"department_results": [run_department_worker(state)]}


def _synthesize(state: RFPState) -> dict[str, Any]:
    results = state.get("department_results", [])
    handoff = {
        "ticket_id": state["ticket_id"],
        "workstreams": results,
        "departments_needed": state.get("departments_needed", []),
        "metadata": state.get("metadata", {}),
    }
    return {"handoff_payload": handoff}


def build_rfp_intake_graph():
    """Build the isolated LangGraph intake workflow; workers fan out in parallel."""
    graph = StateGraph(RFPState)
    graph.add_node("classifier", _classify)
    graph.add_node("extract_metadata", _extract_metadata)
    graph.add_node("department_worker", _worker)
    graph.add_node("synthesizer", _synthesize)
    graph.add_edge(START, "classifier")
    graph.add_conditional_edges("classifier", _route_classification, {"extract_metadata": "extract_metadata", END: END})
    graph.add_conditional_edges("extract_metadata", _dispatch_workers, ["department_worker"])
    graph.add_edge("department_worker", "synthesizer")
    graph.add_edge("synthesizer", END)
    return graph.compile()


rfp_intake_graph = build_rfp_intake_graph()