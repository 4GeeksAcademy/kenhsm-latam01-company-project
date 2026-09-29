from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

CSV_CATEGORIES = ("CUSTOMER_COMPLAINT", "EQUIPMENT", "SUPPLY", "FOOD_QUALITY", "STAFF")
CSV_STATUSES = ("OPEN", "CLOSED", "DISCARDED")
CSV_LOCATIONS = tuple([f"COL-{number:02d}" for number in range(1, 11)] + [f"FLA-{number:02d}" for number in range(1, 5)])
MODEL_CATEGORIES = ("equipment_failure", "supply_issue", "customer_complaint", "staff_issue", "facility_issue", "pos_system", "delivery_issue", "other")
MODEL_STATUSES = ("open", "in_progress", "resolved", "discarded")
MODEL_ORIGINS = ("customer", "branch", "internal")
MODEL_BRANCHES = ("central", "medellin_centro", "medellin_laureles", "medellin_envigado", "medellin_bello", "medellin_itagui", "bogota_chapinero", "bogota_usaquen", "cali_granada", "barranquilla_norte", "miami_doral", "miami_hialeah", "miami_kendall", "orlando_international", "fort_lauderdale")
CATEGORY_MAP = {"CUSTOMER_COMPLAINT": "customer_complaint", "EQUIPMENT": "equipment_failure", "SUPPLY": "supply_issue", "FOOD_QUALITY": "customer_complaint", "STAFF": "staff_issue"}
STATUS_MAP = {"OPEN": "open", "CLOSED": "resolved", "DISCARDED": "discarded"}
BRANCH_MAP = {"COL-01": "medellin_centro", "COL-02": "medellin_laureles", "COL-03": "medellin_envigado", "COL-04": "medellin_bello", "COL-05": "medellin_itagui", "COL-06": "bogota_chapinero", "COL-07": "bogota_usaquen", "COL-08": "cali_granada", "COL-09": "barranquilla_norte", "COL-10": "central", "FLA-01": "miami_doral", "FLA-02": "miami_hialeah", "FLA-03": "miami_kendall", "FLA-04": "orlando_international"}


def clean(value: object) -> str:
    return str(value or "").strip()


def validate_csv_row(row: Mapping[str, object]) -> tuple[set[str], int | None]:
    reasons: set[str] = set()
    location, category, description = clean(row.get("location_id")), clean(row.get("category")), clean(row.get("description"))
    status, reporter, raw_score = clean(row.get("status")), clean(row.get("reporter_id")), clean(row.get("satisfaction_score"))
    if location not in CSV_LOCATIONS: reasons.add("missing_location_id")
    if category not in CSV_CATEGORIES: reasons.add("invalid_or_missing_category")
    if len(description) < 5: reasons.add("empty_description")
    if not reporter: reasons.add("missing_reporter_id")
    if status not in CSV_STATUSES: reasons.add("invalid_or_missing_status")
    score = None
    if raw_score:
        try: score = int(raw_score)
        except ValueError: reasons.add("score_out_of_range")
        else:
            if not 1 <= score <= 5: reasons.add("score_out_of_range")
    elif status == "CLOSED":
        reasons.add("closed_without_score")
    return reasons, score


def validate_incident_payload(payload: Mapping[str, object]) -> dict[str, str]:
    errors = {}
    for field in ("title", "description", "category", "status", "origin", "branch"):
        if not clean(payload.get(field)): errors[field] = "Este campo es obligatorio."
    for field, allowed in (("category", MODEL_CATEGORIES), ("status", MODEL_STATUSES), ("origin", MODEL_ORIGINS), ("branch", MODEL_BRANCHES)):
        value = clean(payload.get(field))
        if value and value not in allowed: errors[field] = "El valor no está permitido."
    return errors


def transform_csv_row(row: Mapping[str, object], *, now: datetime | None = None) -> dict[str, object]:
    description = clean(row.get("description"))
    created_at = datetime.strptime(clean(row["date"]), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return {"title": description[:120].strip(), "description": description, "category": CATEGORY_MAP[clean(row["category"])], "status": STATUS_MAP[clean(row["status"])], "origin": "customer", "branch": BRANCH_MAP.get(clean(row.get("location_id")), "central"), "created_at": created_at, "updated_at": now or created_at}