"""Reusable validation and aggregation logic for Brasaland incident reports."""

from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping

CATEGORIES = (
    "CUSTOMER_COMPLAINT",
    "EQUIPMENT",
    "SUPPLY",
    "FOOD_QUALITY",
    "STAFF",
)
STATUSES = ("OPEN", "CLOSED", "DISCARDED")
LOCATIONS = tuple(
    [f"COL-{number:02d}" for number in range(1, 11)]
    + [f"FLA-{number:02d}" for number in range(1, 5)]
)
REQUIRED_COLUMNS = (
    "incident_id",
    "date",
    "location_id",
    "category",
    "description",
    "status",
    "reporter_id",
)


@dataclass(frozen=True)
class AnalysisResult:
    total_records: int
    valid_records: int
    invalid_records: int
    invalid_breakdown: dict[str, int]
    by_category: dict[str, int]
    by_status: dict[str, int]
    satisfaction_counts: dict[int, int]
    scored_closed_cases: int
    closed_cases: int
    average_satisfaction: float | None

    def to_dict(self) -> dict:
        return {
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "invalid_breakdown": self.invalid_breakdown,
            "by_category": self.by_category,
            "by_status": self.by_status,
            "satisfaction": {
                "closed_cases": self.closed_cases,
                "scored_cases": self.scored_closed_cases,
                "average": self.average_satisfaction,
                "counts": {str(score): count for score, count in self.satisfaction_counts.items()},
            },
        }


def _clean(value: object) -> str:
    return str(value or "").strip()


def _validate_row(row: Mapping[str, object]) -> tuple[set[str], int | None]:
    location = _clean(row.get("location_id"))
    category = _clean(row.get("category"))
    description = _clean(row.get("description"))
    reporter = _clean(row.get("reporter_id"))
    status = _clean(row.get("status"))
    raw_score = _clean(row.get("satisfaction_score"))
    reasons: set[str] = set()

    if location not in LOCATIONS:
        reasons.add("missing_location_id")
    if category not in CATEGORIES:
        reasons.add("invalid_or_missing_category")
    if len(description) < 5:
        reasons.add("empty_description")
    if not reporter:
        reasons.add("missing_reporter_id")
    if status not in STATUSES:
        reasons.add("invalid_or_missing_status")

    score: int | None = None
    if raw_score:
        try:
            score = int(raw_score)
        except ValueError:
            reasons.add("score_out_of_range")
        else:
            if not 1 <= score <= 5:
                reasons.add("score_out_of_range")
    elif status == "CLOSED":
        reasons.add("closed_without_score")

    return reasons, score


def analyze_rows(rows: Iterable[Mapping[str, object]]) -> AnalysisResult:
    invalid_breakdown = Counter(
        {
            "missing_location_id": 0,
            "invalid_or_missing_category": 0,
            "empty_description": 0,
            "missing_reporter_id": 0,
            "closed_without_score": 0,
            "score_out_of_range": 0,
            "invalid_or_missing_status": 0,
        }
    )
    by_category = Counter({category: 0 for category in CATEGORIES})
    by_status = Counter({status: 0 for status in STATUSES})
    satisfaction_counts = Counter({score: 0 for score in range(1, 6)})
    valid_records = 0
    closed_cases = 0
    scored_closed_cases = 0
    score_total = 0
    total_records = 0

    for row in rows:
        total_records += 1
        reasons, score = _validate_row(row)
        for reason in reasons:
            invalid_breakdown[reason] += 1
        if reasons:
            continue

        valid_records += 1
        category = _clean(row.get("category"))
        status = _clean(row.get("status"))
        by_category[category] += 1
        by_status[status] += 1
        if status == "CLOSED":
            closed_cases += 1
            if score is not None:
                scored_closed_cases += 1
                satisfaction_counts[score] += 1
                score_total += score

    average = score_total / scored_closed_cases if scored_closed_cases else None
    return AnalysisResult(
        total_records=total_records,
        valid_records=valid_records,
        invalid_records=total_records - valid_records,
        invalid_breakdown=dict(invalid_breakdown),
        by_category=dict(by_category),
        by_status=dict(by_status),
        satisfaction_counts=dict(satisfaction_counts),
        scored_closed_cases=scored_closed_cases,
        closed_cases=closed_cases,
        average_satisfaction=average,
    )


def analyze_csv_text(csv_text: str) -> AnalysisResult:
    if not csv_text.strip():
        raise ValueError("El fichero CSV está vacío.")
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("El fichero CSV debe incluir una fila de encabezado.")
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(missing_columns)}")
    return analyze_rows(reader)


def export_metrics(result: AnalysisResult) -> str:
    rows = [
        ("total_records", result.total_records, ""),
        ("valid_records", result.valid_records, _percentage(result.valid_records, result.total_records)),
        ("invalid_records", result.invalid_records, _percentage(result.invalid_records, result.total_records)),
    ]
    rows.extend((f"invalid_{key}", value, "") for key, value in result.invalid_breakdown.items() if value)
    rows.extend((f"category_{key}", value, _percentage(value, result.valid_records)) for key, value in result.by_category.items())
    rows.extend((f"status_{key}", value, _percentage(value, result.valid_records)) for key, value in result.by_status.items())
    rows.extend((f"satisfaction_score_{key}", value, "") for key, value in result.satisfaction_counts.items())
    rows.append(("satisfaction_average", result.average_satisfaction if result.average_satisfaction is not None else "", ""))

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("metric", "value", "percentage"))
    writer.writerows(rows)
    return output.getvalue()


def _percentage(value: int, total: int) -> str:
    return f"{(value / total * 100):.1f}" if total else "0.0"
