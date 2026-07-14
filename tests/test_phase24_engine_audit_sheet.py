import csv
import tempfile
import unittest
from pathlib import Path

from namengine.core.engine_audit import (
    SHEET_COLUMNS,
    run_engine_audit,
    summarize_engine_audit,
    write_engine_audit_csv,
)
from namengine.core.evals import load_taste_engine_fixtures


class PhaseTwentyFourEngineAuditSheetTest(unittest.TestCase):
    def test_lane_discovery_audit_writes_google_sheets_ready_csv(self):
        fixture = next(
            item for item in load_taste_engine_fixtures() if item.id == "baby-classic-soft-familiar"
        )
        rows = run_engine_audit([fixture], rounds=3, use_ai=False, run_id="test-run")

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].round_goal, "best-guess discovery")
        self.assertEqual(rows[0].lane_label, "core fit")
        self.assertIn("Highest-confidence", rows[0].lane_description)
        self.assertEqual(rows[1].round_goal, "nearby alternatives")
        self.assertEqual(rows[1].lane_label, "adjacent style")
        self.assertTrue(rows[0].pass_constraints)
        self.assertLessEqual(rows[1].previous_overlap_pct, 0.30)

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = write_engine_audit_csv(rows, Path(tmpdir) / "audit.csv")
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                csv_rows = list(reader)

        self.assertEqual(reader.fieldnames, SHEET_COLUMNS)
        self.assertEqual(csv_rows[0]["run_id"], "test-run")
        self.assertIn("judge_score", csv_rows[0])
        self.assertIn("judge_on_brief_1_5", csv_rows[0])
        self.assertIn("judge_name_quality_1_5", csv_rows[0])
        self.assertIn("judge_lane_discovery_1_5", csv_rows[0])
        self.assertIn("judge_would_save_any", csv_rows[0])
        self.assertIn("judge_names_to_cut", csv_rows[0])
        self.assertIn("judge_notes", csv_rows[0])
        self.assertIn("action_needed", csv_rows[0])
        self.assertIn("review_question", csv_rows[0])
        self.assertIn("lane_label", csv_rows[0])
        self.assertIn("lane_description", csv_rows[0])
        self.assertIn("top_names", csv_rows[0])

    def test_summary_flags_failed_and_passed_rows(self):
        fixture = next(
            item for item in load_taste_engine_fixtures() if item.id == "baby-rare-strong-distinctive"
        )
        rows = run_engine_audit([fixture], rounds=2, use_ai=False, run_id="test-summary")
        summary = summarize_engine_audit(rows)

        self.assertEqual(summary["fixture_count"], 1)
        self.assertEqual(summary["round_count"], 2)
        self.assertEqual(summary["row_count"], 2)
        self.assertIn("average_score", summary)
        self.assertEqual(summary["passed_count"] + summary["failed_count"], 2)

    def test_active_baby_pet_business_audit_gate_is_green(self):
        rows = run_engine_audit(load_taste_engine_fixtures(), rounds=4, use_ai=False, run_id="active-gate")
        summary = summarize_engine_audit(rows)

        self.assertEqual(summary["fixture_count"], 20)
        self.assertEqual(summary["row_count"], 80)
        self.assertEqual(summary["failed_rows"], [])
        self.assertEqual(summary["passed_count"], 80)


if __name__ == "__main__":
    unittest.main()
