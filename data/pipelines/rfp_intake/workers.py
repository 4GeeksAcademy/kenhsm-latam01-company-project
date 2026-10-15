"""Department-scoped extract selection and question handling."""

from __future__ import annotations

import re
from typing import Any

from .graph import DEPARTMENTS

_KEYWORDS = {
    "marketing": ("brand", "marca", "exclusive", "exclusiv", "co-brand", "validez", "validity"),
    "operaciones": ("capacity", "capacidad", "staff", "personal", "setup", "montaje", "event", "evento", "resort", "catering", "comensales", "empleados"),
    "procurement": ("volume", "volumen", "supply", "proveedor", "ingredients", "insumos", "delivery", "entrega", "budget", "presupuesto", "catering", "comensales", "empleados"),
    "training": ("recipe", "receta", "menu", "menú", "standard", "estándar", "certification", "certificación", "chef", "autor"),
}
_QUESTION_FIELDS = {
    "marketing": ("client_name", "deadline", "marca", "área no configurada", "contradictorios"),
    "operaciones": ("scope", "location", "deadline", "alcance contradictorio"),
    "procurement": ("scope", "budget_range", "deadline", "alcance contradictorio"),
    "training": ("scope", "deadline", "alcance contradictorio"),
}


def extract_relevant_excerpt(markdown: str, department_id: str) -> str:
    keywords = _KEYWORDS[department_id]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n|(?<=[.!?])\s+", markdown) if part.strip()]
    matches = [part for part in paragraphs if any(word in part.casefold() for word in keywords)]
    if department_id == "procurement":
        matches.extend(part for part in paragraphs if re.search(r"\b(?:USD|US\$|COP|\$)\s?[\d,.]+|\b\d[\d,.]*\s+(?:comensales|empleados|personas)\b", part, re.I) and part not in matches)
    return "\n".join(matches[:8])


def run_department_worker(state: dict[str, Any]) -> dict[str, Any]:
    department_id = state["department_id"]
    details = DEPARTMENTS[department_id]
    metadata = state.get("metadata", {})
    relevant_fields = _QUESTION_FIELDS[department_id]
    open_questions = [
        question for question in metadata.get("open_questions", [])
        if any(field in question.casefold() for field in relevant_fields)
    ]
    excerpt = state.get("excerpt", "")
    return {
        "department_id": department_id,
        "department_name": details["name"],
        "contact": details["contact"],
        "key_aspects": {
            "focus": details["focus"],
            "source_extracts": [excerpt] if excerpt else [],
            "open_questions": open_questions,
        },
    }