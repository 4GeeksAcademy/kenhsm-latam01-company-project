from fastapi.testclient import TestClient

from brasaland_api.core.config import Settings
from brasaland_api.main import app

client = TestClient(app)


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


def test_telemetry_endpoint_setting_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("TELEMETRY_ENDPOINT", "https://telemetry.example.test/events")

    assert Settings().telemetry_endpoint == "https://telemetry.example.test/events"