"""Execute document conversion, the intake graph, and deterministic handoff checks."""

from pathlib import Path
from typing import Any

from .intake import convert_pdf_to_markdown
from .quality import annotate_handoff_questions
from .runtime import rfp_intake_graph


def run_rfp_intake(ticket_id: str, pdf_path: str | Path) -> dict[str, Any]:
    markdown = convert_pdf_to_markdown(pdf_path)
    result = rfp_intake_graph.invoke({"ticket_id": ticket_id, "markdown": markdown})
    if result.get("classification", {}).get("is_valid"):
        annotate_handoff_questions(result, markdown)
    return result