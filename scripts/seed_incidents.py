from __future__ import annotations

import argparse
import csv
import os
import sys
import uuid
from collections import Counter
from pathlib import Path

from tinydb import Query, TinyDB

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/shared/src"))
from brasaland_shared.incidents import transform_csv_row, validate_csv_row


def seed(csv_path: Path, db_path: Path) -> tuple[int, int, Counter[str]]:
    with csv_path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError("El CSV debe incluir una fila de encabezado.")
        required = {"date", "category", "description", "status", "location_id"}
        missing = sorted(required - set(reader.fieldnames))
        if missing:
            raise ValueError(f"Faltan columnas requeridas: {', '.join(missing)}")
        rows = list(reader)

    table = TinyDB(db_path).table("incidents")
    invalid = Counter[str]()
    inserted = skipped = 0
    for row in rows:
        reasons, _ = validate_csv_row(row)
        if reasons:
            invalid.update(reasons)
            continue
        title_key = row.get("description", "").strip()[:120].strip()
        source_key = (row.get("incident_id") or row.get("ticket_id") or f"{title_key}|{row.get('date', '')}").strip()
        if table.get(Query().source_key == source_key):
            skipped += 1
            continue
        try:
            values = transform_csv_row(row)
        except (KeyError, ValueError):
            invalid["invalid_date"] += 1
            continue
        table.insert({"id": str(uuid.uuid4()), "source_key": source_key, **{key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in values.items()}})
        inserted += 1
    return inserted, skipped, invalid


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga el histórico CSV de incidencias en TinyDB.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--db", type=Path, default=Path(os.getenv("TINYDB_PATH", "services/brasaland-api/data/db.json")))
    args = parser.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    inserted, skipped, invalid = seed(args.csv_path, args.db)
    print(f"Incidencias insertadas: {inserted}")
    print(f"Duplicados omitidos: {skipped}")
    print(f"Registros inválidos omitidos: {sum(invalid.values())}")
    for reason, count in sorted(invalid.items()):
        print(f"  {reason}: {count}")


if __name__ == "__main__":
    main()