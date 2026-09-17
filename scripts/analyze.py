#!/usr/bin/env python3
"""Command-line analyzer for Brasaland incident CSV files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from incident_analysis import AnalysisResult, analyze_csv_text, export_metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Analiza reportes de incidentes de Brasaland.")
    parser.add_argument("csv_path", type=Path, help="Ruta al fichero CSV de incidentes")
    args = parser.parse_args()

    try:
        csv_text = args.csv_path.read_text(encoding="utf-8-sig")
        result = analyze_csv_text(csv_text)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Error al leer el fichero: {error}", file=sys.stderr)
        return 1

    print_report(args.csv_path.name, result)
    answer = input("¿Deseas exportar los resultados a CSV? [s / n]: ").strip().lower()
    if answer == "s":
        Path("results.csv").write_text(export_metrics(result), encoding="utf-8", newline="")
        print("Resultados exportados a results.csv")
    return 0


def print_report(source_name: str, result: AnalysisResult) -> None:
    print("=" * 60)
    print("  BRASALAND — INCIDENT REPORT ANALYSIS")
    print(f"  Source file: {source_name}")
    print("=" * 60)
    print()
    print(f"TOTAL RECORDS IN FILE .......... {result.total_records}")
    print(f"  ├─ Valid records ................ {result.valid_records}")
    print(f"  └─ Invalid / incomplete .......... {result.invalid_records}")
    print()
    print("INVALID RECORDS BREAKDOWN")
    labels = {
        "missing_location_id": "Missing location_id",
        "invalid_or_missing_category": "Invalid or missing category",
        "empty_description": "Empty description",
        "missing_reporter_id": "Missing reporter_id",
        "closed_without_score": "Closed case, no score",
        "score_out_of_range": "Score outside range",
        "invalid_or_missing_status": "Invalid or missing status",
    }
    for key, label in labels.items():
        print(f"  ├─ {label:<29} {result.invalid_breakdown[key]}")
    print()
    print("BREAKDOWN BY CATEGORY (valid records)")
    _print_breakdown(result.by_category, result.valid_records)
    print()
    print("BREAKDOWN BY STATUS (valid records)")
    _print_breakdown(result.by_status, result.valid_records)
    print()
    print("SATISFACTION INDEX (closed cases)")
    print(f"  Scored cases: {result.scored_closed_cases} of {result.closed_cases}")
    average = f"{result.average_satisfaction:.2f}" if result.average_satisfaction is not None else "N/A"
    print(f"  Average score: {average} / 5.00")
    score_labels = {1: "Very dissatisfied", 2: "Dissatisfied", 3: "Neutral", 4: "Satisfied", 5: "Very satisfied"}
    for score, label in score_labels.items():
        print(f"  ├─ Score {score} ({label:<17}) ... {result.satisfaction_counts[score]}")
    print()
    print("=" * 60)


def _print_breakdown(values: dict[str, int], total: int) -> None:
    for label, value in values.items():
        percentage = value / total * 100 if total else 0
        print(f"  ├─ {label:<28} {value:>3}  ({percentage:.1f}%)")


if __name__ == "__main__":
    raise SystemExit(main())
