"""Deterministic handoff checks for unowned departments and conflicting scope."""

from __future__ import annotations

import re
from typing import Any

_UNROUTED_DEPARTMENTS = {
    "finanzas": "finanzas",
    "finance": "finance",
    "legal": "legal",
    "rrhh": "RR. HH.",
    "human resources": "Human Resources",
    "tecnologia": "Tecnología",
    "technology": "Technology",
    "it": "IT",
    "ventas": "Ventas",
    "sales": "Sales",
}
_SCOPE_UNITS = ("comensales", "empleados", "personas", "resorts", "ubicaciones", "locations")


def annotate_handoff_questions(result: dict[str, Any], markdown: str) -> None:
    """Preserve unmapped requests and conflicting source values for Marketing review."""
    questions = result.get("metadata", {}).setdefault("open_questions", [])
    text = markdown.casefold()
    for term, label in _UNROUTED_DEPARTMENTS.items():
        pattern = rf"\b(?:departamento|department|[áa]rea|team)\s+(?:de\s+|of\s+)?{re.escape(term)}\b"
        if re.search(pattern, text):
            question = f"Derivar manualmente la solicitud del área no configurada: {label}."
            if question not in questions:
                questions.append(question)

    for unit in _SCOPE_UNITS:
        values = set(re.findall(rf"\b(\d[\d,.]*)\s+{re.escape(unit)}\b", text))
        if len(values) > 1:
            question = f"El documento menciona alcances contradictorios para {unit}: {', '.join(sorted(values))}. Confirmar con Marketing; no seleccionar un valor automáticamente."
            if question not in questions:
                questions.append(question)

    marketing_section = next(
        (section for section in result.get("department_results", []) if section.get("department_id") == "marketing"),
        None,
    )
    if marketing_section:
        aspects = marketing_section.setdefault("key_aspects", {})
        aspects.setdefault("open_questions", []).extend(
            question for question in questions if question not in aspects.get("open_questions", [])
        )
    if result.get("handoff_payload"):
        result["handoff_payload"]["metadata"] = result["metadata"]
        result["handoff_payload"]["workstreams"] = result.get("department_results", [])