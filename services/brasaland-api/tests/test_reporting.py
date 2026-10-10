from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from brasaland_api.core.deps import get_current_user, require_admin
from brasaland_api.main import app


class ReportingEndpointTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_user] = lambda: None
        app.dependency_overrides[require_admin] = lambda: None
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_latest_run_endpoint_returns_execution_metadata(self):
        record = {
            "run_id": "run-123",
            "flow_name": "weekly_location_performance_flow",
            "trigger_type": "scheduled",
            "week_start": "2026-10-05",
            "status": "Completed",
            "phase": "complete",
            "started_at": "2026-10-10T06:00:00+00:00",
            "ended_at": "2026-10-10T06:01:00+00:00",
            "source_counts": {"inbound_order_created": 25},
            "source_min_timestamp": None,
            "source_max_timestamp": None,
            "source_watermark": None,
            "output_rows": 14,
            "records_processed": 25,
            "error_code": None,
            "error_message": None,
            "errors": [],
            "local_mode": False,
        }
        with patch("services.reporting.router.run_store.get_latest_pipeline_run", return_value=record):
            response = self.client.get("/reporting/pipeline-runs/latest")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], record["status"])
        self.assertEqual(response.json()["records_processed"], record["records_processed"])
        self.assertTrue(response.json()["started_at"].startswith("2026-10-10T06:00:00"))

    def test_weekly_kpi_endpoint_matches_dashboard_contract(self):
        report = {
            "week_start": "2026-10-05",
            "locations": [
                {
                    "location_id": "COL-01",
                    "country": "CO",
                    "total_purchase_cost": 1000,
                    "total_waste_cost": 75,
                    "waste_ratio": 0.075,
                    "stockout_events_count": 2,
                    "price_alert_events_count": 1,
                    "currency": "COP",
                }
            ],
        }
        with patch("services.reporting.router.run_store.query_weekly_location_performance", return_value=report):
            response = self.client.get("/reporting/weekly-location-performance?week_start=2026-10-05")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), report)

    def test_manual_run_queues_the_shared_pipeline_entrypoint(self):
        with patch("services.reporting.router.trigger_weekly_location_performance_flow") as trigger:
            response = self.client.post("/reporting/pipeline-runs?week_start=2026-10-05")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "scheduled")
        trigger.assert_called_once()

    def test_reporting_endpoints_require_authentication(self):
        app.dependency_overrides.clear()

        response = self.client.get("/reporting/pipeline-runs/latest")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()