from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from data.pipelines import run_store


class PipelineStorageTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_REPORTING_WRITE_KEY": "write-key",
        },
    )
    @patch("data.pipelines.run_store.httpx.post")
    def test_load_uses_business_key_upsert_in_reporting_schema(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        post.return_value = response
        rows = [{"location_id": "COL-01", "week_start": "2026-10-05", "total_purchase_cost": 100}]

        loaded = run_store.load_weekly_performance(rows)

        self.assertEqual(loaded, 1)
        call = post.call_args.kwargs
        self.assertEqual(call["params"], {"on_conflict": "location_id,week_start"})
        self.assertEqual(call["json"], rows)
        self.assertEqual(call["headers"]["Content-Profile"], "reporting")
        self.assertIn("resolution=merge-duplicates", call["headers"]["Prefer"])

    def test_local_run_metadata_is_structured_and_latest_is_readable(self):
        record = {"run_id": "local-run", "status": "Completed", "records_processed": 4}
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "runs.jsonl"
            with patch.object(run_store, "RUN_LOG_PATH", log_path):
                run_store.persist_run_metadata(record, local_mode=True)
                self.assertEqual(run_store.get_latest_pipeline_run(), record)
                self.assertEqual(json.loads(log_path.read_text(encoding="utf-8")), record)


if __name__ == "__main__":
    unittest.main()