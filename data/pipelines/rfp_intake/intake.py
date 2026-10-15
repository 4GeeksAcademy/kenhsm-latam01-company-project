"""PDF conversion and metadata extraction for the RFP intake pipeline."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def convert_pdf_to_markdown(pdf_path: str | Path) -> str:
    """Convert a PDF to Markdown before it reaches any agent node."""
    from markitdown import MarkItDown

    markdown = MarkItDown().convert(str(pdf_path)).text_content
    if not markdown or not markdown.strip():
        raise ValueError("El PDF no contiene texto que se pueda analizar.")
    return markdown.strip()


def calculate_readability(markdown: str) -> dict[str, Any]:
    words = re.findall(r"\b[\w'-]+\b", markdown, flags=re.UNICODE)
    metrics: dict[str, Any] = {
        "word_count": len(words),
        "estimated_input_tokens": round(len(words) * 1.3),
        "flesch_kincaid_grade": None,
        "gunning_fog": None,
    }
    if len(words) < 100:
        metrics["metrics_note"] = "Se requieren al menos 100 palabras para estimar legibilidad con estabilidad."
        return metrics

    from readability import Readability

    readability = Readability(markdown)
    for metric_name, measure in (
        ("flesch_kincaid_grade", readability.flesch_kincaid),
        ("gunning_fog", readability.gunning_fog),
    ):
        try:
            metrics[metric_name] = round(float(measure().score), 2)
        except (ValueError, ZeroDivisionError):
            metrics[metric_name] = None
    return metrics


def _first_match(patterns: tuple[str, ...], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,:;\n\t")
    return None


def extract_rfp_metadata(markdown: str) -> dict[str, Any]:
    """Extract only evidence present in the converted document."""
    client_name = _first_match(
        (
            r"(?:cliente|client|de|from)\s*[:\-]?\s*(Sunset Bay Resorts|Andes Tech Solutions)",
            r"(?:cliente|client|de|from)\s*[:\-]?\s*([A-Z][\w&.' -]{2,50}?)(?=\s+(?:solicita|busca|requests|seeks|invita))",
        ),
        markdown,
    )
    service_type = _first_match(
        (r"\b(catering(?:\s+(?:semanal|recurrente))?|concesi[oó]n(?:\s+co.?branded)?|co.?branding)\b",),
        markdown,
    )
    location = _first_match(
        (r"\b(Florida|Medell[ií]n|Miami|Orlando|Bogot[aá])\b",),
        markdown,
    )
    scope_sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", markdown)
        if re.search(r"\d|comensales|empleados|resorts|ubicaciones|semanal|mensual|anual|men[uú]", sentence, re.I)
    ]
    deadline = _first_match(
        (r"(?:fecha l[ií]mite|deadline|responder antes de|response due)\s*[:\-]?\s*([^\n.;]{3,60})",),
        markdown,
    )
    budget_range = _first_match(
        (r"((?:USD|US\$|\$|COP)\s?[\d,.]+(?:\s*(?:-|a|to)\s*(?:USD|US\$|\$|COP)?\s?[\d,.]+)?(?:\s*(?:\/\s*a[nñ]o|anual|por a[nñ]o))?)",),
        markdown,
    )
    duration = _first_match((r"(\d+\s+meses|\d+\s+a[nñ]os?|anual|semanal)",), markdown)
    if duration and scope_sentences:
        scope_sentences.append(f"Duración/recurrencia indicada: {duration}")

    open_questions = [
        field for field, value in (
            ("client_name", client_name),
            ("location", location),
            ("service_type", service_type),
            ("scope", scope_sentences),
            ("deadline", deadline),
            ("budget_range", budget_range),
        ) if not value
    ]
    return {
        "client_name": client_name,
        "location": location,
        "service_type": service_type,
        "scope": scope_sentences or None,
        "deadline": deadline,
        "budget_range": budget_range,
        "open_questions": open_questions,
        "readability_metrics": calculate_readability(markdown),
    }