"""Graceful readability wrapper when optional tokenizer data is unavailable."""

from __future__ import annotations

import re
from typing import Any

from . import metrics


def calculate_readability(markdown: str) -> dict[str, Any]:
    try:
        return metrics.calculate_readability(markdown)
    except ModuleNotFoundError as error:
        if error.name not in {"readability", "nltk"}:
            raise
    words = re.findall(r"\b[\w'-]+\b", markdown, flags=re.UNICODE)
    flesch_kincaid, gunning_fog = metrics._fallback_scores(markdown, words)
    return {
        "word_count": len(words),
        "estimated_input_tokens": round(len(words) * 1.3),
        "flesch_kincaid_grade": flesch_kincaid,
        "gunning_fog": gunning_fog,
        "metrics_note": "Estimación local: py-readability-metrics o NLTK no están disponibles.",
    }