"""Offline-safe readability and token-cost estimates for converted documents."""

from __future__ import annotations

import re
from typing import Any


def _syllable_count(word: str) -> int:
    normalized = re.sub(r"[^a-z]", "", word.casefold())
    groups = re.findall(r"[aeiouy]+", normalized)
    count = len(groups)
    if normalized.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _fallback_scores(text: str, words: list[str]) -> tuple[float | None, float | None]:
    sentences = [part for part in re.split(r"[.!?]+", text) if part.strip()]
    if not words or not sentences:
        return None, None
    syllables = sum(_syllable_count(word) for word in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)
    complex_words = sum(_syllable_count(word) >= 3 for word in words)
    flesch_kincaid = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
    gunning_fog = 0.4 * (words_per_sentence + 100 * complex_words / len(words))
    return round(flesch_kincaid, 2), round(gunning_fog, 2)


def calculate_readability(markdown: str) -> dict[str, Any]:
    words = re.findall(r"\b[\w'-]+\b", markdown, flags=re.UNICODE)
    result: dict[str, Any] = {
        "word_count": len(words),
        "estimated_input_tokens": round(len(words) * 1.3),
        "flesch_kincaid_grade": None,
        "gunning_fog": None,
    }
    if len(words) < 100:
        result["metrics_note"] = "Se requieren al menos 100 palabras para estimar legibilidad con estabilidad."
        return result

    try:
        from readability import Readability

        readability = Readability(markdown)
        result["flesch_kincaid_grade"] = round(float(readability.flesch_kincaid().score), 2)
        result["gunning_fog"] = round(float(readability.gunning_fog().score), 2)
    except (LookupError, ValueError, ZeroDivisionError):
        result["flesch_kincaid_grade"], result["gunning_fog"] = _fallback_scores(markdown, words)
        result["metrics_note"] = "Estimación local sin recursos NLTK externos."
    return result