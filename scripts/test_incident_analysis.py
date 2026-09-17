import unittest

from incident_analysis import analyze_rows, export_metrics


HEADER = {
    "incident_id": "BRS-000001",
    "date": "2026-01-01",
    "location_id": "COL-01",
    "description": "Incidente operativo válido",
    "reporter_id": "MGR-01",
}


class IncidentAnalysisTests(unittest.TestCase):
    def test_context_distribution_and_average(self):
        rows = []
        category_counts = {
            "CUSTOMER_COMPLAINT": 29,
            "EQUIPMENT": 17,
            "SUPPLY": 22,
            "FOOD_QUALITY": 19,
            "STAFF": 9,
        }
        status_counts = {"OPEN": 32, "CLOSED": 50, "DISCARDED": 14}
        scores = [1] * 4 + [2] * 6 + [3] * 12 + [4] * 19 + [5] * 9
        score_index = 0
        index = 0
        for category, count in category_counts.items():
            for _ in range(count):
                status = next(status for status, remaining in status_counts.items() if remaining > 0)
                status_counts[status] -= 1
                row = {**HEADER, "incident_id": f"BRS-{index + 1:06d}", "category": category, "status": status}
                if status == "CLOSED":
                    row["satisfaction_score"] = str(scores[score_index])
                    score_index += 1
                rows.append(row)
                index += 1
        rows.extend([
            {**HEADER, "incident_id": "BRS-000101", "location_id": "", "category": "SUPPLY", "status": "OPEN"},
            {**HEADER, "incident_id": "BRS-000102", "category": "UNKNOWN", "status": "OPEN"},
            {**HEADER, "incident_id": "BRS-000103", "description": "x", "category": "STAFF", "status": "OPEN"},
            {**HEADER, "incident_id": "BRS-000104", "category": "STAFF", "status": "CLOSED", "satisfaction_score": ""},
        ])

        result = analyze_rows(rows)
        self.assertEqual(result.total_records, 100)
        self.assertEqual(result.valid_records, 96)
        self.assertEqual(result.invalid_records, 4)
        self.assertEqual(result.by_category, category_counts)
        self.assertEqual(result.by_status, {"OPEN": 32, "CLOSED": 50, "DISCARDED": 14})
        self.assertEqual(result.satisfaction_counts, {1: 4, 2: 6, 3: 12, 4: 19, 5: 9})
        self.assertEqual(result.average_satisfaction, 3.46)
        self.assertEqual(result.invalid_breakdown["missing_location_id"], 1)
        self.assertEqual(result.invalid_breakdown["invalid_or_missing_category"], 1)
        self.assertEqual(result.invalid_breakdown["empty_description"], 1)
        self.assertEqual(result.invalid_breakdown["closed_without_score"], 1)
        self.assertTrue(export_metrics(result).startswith("metric,value,percentage\n"))


if __name__ == "__main__":
    unittest.main()
