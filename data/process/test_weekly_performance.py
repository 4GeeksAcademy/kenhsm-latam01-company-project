from __future__ import annotations

import unittest

from data.process.weekly_performance import transform_weekly_location_metrics


class WeeklyPerformanceTransformTests(unittest.TestCase):
    def test_aggregates_business_kpis_and_keeps_location_currencies_separate(self):
        week_start = "2026-10-05"
        events = [
            {
                "id": "purchase-1",
                "timestamp": "2026-10-05T12:00:00Z",
                "event_type": "inbound_order_created",
                "tags": {"location_id": "COL-01", "country": "CO", "currency": "COP", "quantity": 3, "unit_price": 1200},
            },
            {
                "id": "waste-1",
                "timestamp": "2026-10-06T12:00:00Z",
                "event_type": "stock_waste_registered",
                "tags": {"location_id": "COL-01", "country": "CO", "currency": "COP", "quantity": 2, "unit_cost": 300},
            },
            {
                "id": "stockout-1",
                "timestamp": "2026-10-07T12:00:00Z",
                "event_type": "stock_threshold_triggered",
                "tags": {"location_id": "COL-01", "country": "CO", "currency": "COP"},
            },
            {
                "id": "price-alert-1",
                "timestamp": "2026-10-08T12:00:00Z",
                "event_type": "ingredient_price_variance_detected",
                "tags": {"location_id": "COL-01", "country": "CO", "currency": "COP"},
            },
        ]

        rows = transform_weekly_location_metrics(events, week_start)

        self.assertEqual(len(rows), 14)
        medellin = next(row for row in rows if row["location_id"] == "COL-01")
        miami = next(row for row in rows if row["location_id"] == "FLA-01")
        self.assertEqual(medellin["total_purchase_cost"], 3600)
        self.assertEqual(medellin["total_waste_cost"], 600)
        self.assertEqual(medellin["waste_ratio"], 1 / 6)
        self.assertEqual(medellin["stockout_events_count"], 1)
        self.assertEqual(medellin["price_alert_events_count"], 1)
        self.assertEqual((medellin["country"], medellin["currency"]), ("CO", "COP"))
        self.assertEqual((miami["country"], miami["currency"]), ("US", "USD"))

    def test_deduplicates_repeated_persisted_event_ids(self):
        event = {
            "id": "same-row",
            "timestamp": "2026-10-05T12:00:00Z",
            "event_type": "stock_threshold_triggered",
            "tags": {"location_id": "COL-01", "country": "CO", "currency": "COP"},
        }

        rows = transform_weekly_location_metrics([event, event.copy()], "2026-10-05")

        self.assertEqual(rows[0]["stockout_events_count"], 1)

    def test_rejects_location_currency_mismatch(self):
        event = {
            "id": "bad-location",
            "timestamp": "2026-10-05T12:00:00Z",
            "event_type": "stock_threshold_triggered",
            "tags": {"location_id": "COL-01", "country": "US", "currency": "USD"},
        }

        with self.assertRaisesRegex(ValueError, "country/currency mismatch"):
            transform_weekly_location_metrics([event], "2026-10-05")


if __name__ == "__main__":
    unittest.main()