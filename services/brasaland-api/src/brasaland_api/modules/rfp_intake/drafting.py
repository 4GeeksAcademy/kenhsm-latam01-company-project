"""Backend adapter for persisted Part 1 handoffs and multilingual draft evaluation."""

from __future__ import annotations

import re
from typing import Any

from data.pipelines.rfp_intake import drafting as drafting_graph
from data.pipelines.rfp_intake.drafting_adapter import run_rfp_draft_generation
from data.pipelines.rfp_intake.metrics_adapter import calculate_readability


def evaluate_proposal_readability(draft: str) -> dict[str, Any]:
    metrics = calculate_readability(draft)
    words = re.findall(r"\b[\w'-]+\b", draft, flags=re.UNICODE)
    sentences = [part.strip() for part in re.split(r"[.!?]+", draft) if part.strip()]
    sentence_lengths = [len(re.findall(r"\b[\w'-]+\b", sentence, flags=re.UNICODE)) for sentence in sentences]
    word_count = len(words)
    max_sentence_words = max(sentence_lengths, default=0)
    return {
        "pass": word_count >= 60 and max_sentence_words <= 35,
        "score": metrics.get("flesch_kincaid_grade"),
        "details": {
            "word_count": word_count,
            "max_sentence_words": max_sentence_words,
            "flesch_kincaid_grade": metrics.get("flesch_kincaid_grade"),
            "gunning_fog": metrics.get("gunning_fog"),
            "metrics_note": metrics.get("metrics_note"),
            "score_is_diagnostic_for_spanish": True,
        },
    }


drafting_graph.evaluate_readability = evaluate_proposal_readability