"""Allowed telemetry properties copied from the approved event registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PropertyContract:
    required: frozenset[str]
    allowed: frozenset[str]


def _contract(required: str, optional: str = "") -> PropertyContract:
    required_keys = frozenset(required.split())
    return PropertyContract(required=required_keys, allowed=required_keys | frozenset(optional.split()))


EVENT_PROPERTY_CONTRACTS = {
    "inbound_order_created": _contract(
        "location_id country product_id product_category quantity unit currency supplier_id inbound_order_id unit_price"
    ),
    "outbound_order_created": _contract(
        "location_id country product_id product_category quantity unit currency reason outbound_order_id"
    ),
    "stock_waste_registered": _contract(
        "location_id country product_id product_category quantity unit currency reason outbound_order_id"
    ),
    "stock_threshold_triggered": _contract(
        "location_id country product_id product_category quantity unit currency minimum_quantity threshold_version"
    ),
    "direct_stock_edit_rejected": _contract(
        "location_id country product_id product_category quantity unit currency rejection_code"
    ),
    "ingredient_price_variance_detected": _contract(
        "location_id country product_id product_category quantity unit currency supplier_id current_unit_price historical_unit_price variance_percent threshold_percent inbound_order_id"
    ),
    "inventory_order_validation_failed": _contract(
        "order_type failure_codes item_count", "location_id failed_product_ids"
    ),
    "purchase_order_created": _contract(
        "purchase_order_id supplier_id location_id country currency line_count"
    ),
    "workflow_started": _contract("workflow_id workflow_instance_id entry_source"),
    "workflow_completed": _contract("workflow_id workflow_instance_id elapsed_seconds"),
    "workflow_abandoned": _contract(
        "workflow_id workflow_instance_id last_completed_step elapsed_seconds completion_state"
    ),
    "auth_login_succeeded": _contract("auth_method role client_area"),
    "auth_login_failed": _contract("failure_reason client_area"),
    "session_expired": _contract("expiry_reason session_age_seconds client_area"),
    "access_denied": _contract("resource_type action denial_code http_status actor_role"),
    "user_account_created": _contract("assigned_role creation_source"),
    "user_account_updated": _contract("changed_fields target_role change_source"),
    "user_account_deleted": _contract("deletion_source actor_role"),
    "section_viewed": _contract("section_id client_area navigation_source"),
    "api_latency_recorded": _contract(
        "route_template http_method status_code duration_ms sample_rate service_name"
    ),
    "api_request_failed": _contract(
        "route_template http_method status_code error_code retryable service_name"
    ),
    "frontend_error_captured": _contract(
        "error_fingerprint component_area severity release occurrence_count_bucket"
    ),
    "incident_analysis_completed": _contract(
        "total_records valid_records invalid_records duration_ms file_size_bytes"
    ),
    "incident_analysis_failed": _contract("failure_stage error_code file_size_bytes duration_ms"),
    "background_job_failed": _contract("job_name failure_code attempt_number will_retry duration_ms"),
}


def properties_match_contract(event_type: str, properties: dict[str, object]) -> bool:
    contract = EVENT_PROPERTY_CONTRACTS.get(event_type)
    if contract is None:
        return False
    keys = set(properties)
    return contract.required.issubset(keys) and keys.issubset(contract.allowed)