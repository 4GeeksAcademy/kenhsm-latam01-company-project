from __future__ import annotations

from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient



from brasaland_api.core.config import Settings
from brasaland_api.main import app

client = TestClient(app)


def make_event(properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "eventId": "6ba7b810-9dad-41d1-80b4-00c04fd430c8",
        "timestamp": "2026-09-27T14:05:00Z",
        "sessionId": "session-12345678",
        "userId": None,
        "event_type": "section_viewed",
        "schemaVersion": "1.0.0",
        "requestId": "6ba7b811-9dad-41d1-80b4-00c04fd430c8",
        "properties": properties or {
            "section_id": "operations",
            "client_area": "backoffice",
            "navigation_source": "unknown",
        },
    }


def test_batch_stores_valid_events_and_rejects_invalid_items_individually() -> None:
    invalid_properties = {
        "section_id": "operations",
        "client_area": "backoffice",
        "navigation_source": "unknown",
        "email": "must-not-be-stored@example.com",
    }
    invalid_envelope = {"event_type": "missing_required_fields"}
    with patch("brasaland_api.modules.telemetry.router.insert_events", return_value=1) as insert:
        response = client.post(
            "/telemetry/events",
            json={"events": [make_event(), make_event(invalid_properties), invalid_envelope]},
        )

    assert response.status_code == 200
    assert response.json() == {"received": 3, "stored": 1, "rejected": 2}
    assert insert.call_count == 1
    persisted_batch = insert.call_args.args[0]
    assert len(persisted_batch) == 1
    assert "email" not in persisted_batch[0].properties


def test_batch_with_no_valid_events_does_not_call_storage() -> None:
    with patch("brasaland_api.modules.telemetry.router.insert_events") as insert:
        response = client.post("/telemetry/events", json={"events": [{"event_type": "unknown_event"}]})

    assert response.status_code == 200
    assert response.json() == {"received": 1, "stored": 0, "rejected": 1}
    insert.assert_not_called()


def test_batch_requires_events_array() -> None:
    response = client.post("/telemetry/events", json={"events": {"event_type": "section_viewed"}})
    assert response.status_code == 422
      
      
def test_telemetry_endpoint_accepts_enveloped_batches(caplog) -> None:
    caplog.set_level("INFO", logger="brasaland_api.modules.telemetry.router")
    response = client.post(
        "/telemetry/events",
        json={
            "events": [
                {
                    "eventId": "6ba7b810-9dad-41d1-80b4-00c04fd430c8",
                    "timestamp": "2026-09-27T14:05:00Z",
                    "sessionId": "session-12345678",
                    "userId": None,
                    "event_type": "section_viewed",
                    "schemaVersion": "1.0.0",
                    "requestId": "6ba7b811-9dad-41d1-80b4-00c04fd430c8",
                    "properties": {"section_id": "operations"},
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"received": 1}
    assert "section_viewed" in caplog.text


def test_telemetry_endpoint_rejects_invalid_envelopes() -> None:
    response = client.post("/telemetry/events", json={"events": [{"event_type": "section_viewed"}]})
    assert response.status_code == 422
   


def test_storage_failure_returns_retryable_service_error() -> None:
    from brasaland_api.modules.telemetry.storage import SupabaseStorageError

    with patch(
        "brasaland_api.modules.telemetry.router.insert_events",
        side_effect=SupabaseStorageError("storage unavailable"),
    ):
        response = client.post("/telemetry/events", json={"events": [make_event()]})

    assert response.status_code == 503
    assert response.json() == {"detail": "Telemetry storage is temporarily unavailable"}
    
    
def test_telemetry_endpoint_setting_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("TELEMETRY_ENDPOINT", "https://telemetry.example.test/events")

    assert Settings().telemetry_endpoint == "https://telemetry.example.test/events"
