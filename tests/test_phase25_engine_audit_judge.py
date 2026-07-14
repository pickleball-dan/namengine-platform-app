import csv
import json
import tempfile
import unittest
from pathlib import Path

from judge_engine_audit import judge_row, judge_row_with_ai, read_rows, write_rows
from namengine.core.engine_audit import run_engine_audit, write_engine_audit_csv
from namengine.core.evals import load_taste_engine_fixtures


class FakeAIResponse:
    output_text = json.dumps(
        {
            "on_brief": 4,
            "name_quality": 3,
            "lane_discovery": 4,
            "would_save_any": "Maybe",
            "names_to_cut": ["Testbad"],
            "notes": "Useful lane, but one candidate feels weaker than the rest.",
            "action_needed": "candidate quality review",
        }
    )


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeAIResponse()


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


class PhaseTwentyFiveEngineAuditJudgeTest(unittest.TestCase):
    def test_judge_row_fills_reviewer_columns(self):
        row = {
            "vertical": "baby",
            "passed": "True",
            "signal_hit_count": "5",
            "previous_overlap_pct": "0.0",
            "cumulative_repeat_count": "0",
            "constraint_violations": "",
            "top_names": "Eloise | Cora | Nora | Louisa | Celia | Thea | Lena | Maya",
            "lane_label": "core fit",
        }

        judged = judge_row(row)

        self.assertEqual(judged["judge_on_brief_1_5"], "5")
        self.assertEqual(judged["judge_lane_discovery_1_5"], "5")
        self.assertEqual(judged["judge_would_save_any"], "Yes")
        self.assertEqual(judged["action_needed"], "no action")

    def test_ai_judge_row_uses_schema_response(self):
        fake_client = FakeClient()
        row = {
            "vertical": "business",
            "label": "Business · Clear trustworthy",
            "round_number": "2",
            "lane_label": "brand-shape alternatives",
            "lane_description": "Fresh names that test nearby shapes.",
            "passed": "True",
            "signal_hit_count": "5",
            "previous_overlap_pct": "0.0",
            "constraint_violations": "",
            "top_names": "Clearhaven | Northledger | Testbad",
            "brief_json": json.dumps({"inputs": {"notes": "clear, trustworthy"}}),
        }

        judged = judge_row_with_ai(row, client_factory=lambda: fake_client)

        self.assertEqual(judged["judge_on_brief_1_5"], "4")
        self.assertEqual(judged["judge_name_quality_1_5"], "3")
        self.assertEqual(judged["judge_would_save_any"], "Maybe")
        self.assertEqual(judged["judge_names_to_cut"], "Testbad")
        self.assertEqual(judged["action_needed"], "candidate quality review")
        self.assertIn("response_format", fake_client.responses.calls[0])

    def test_judged_csv_round_trip(self):
        fixture = next(
            item for item in load_taste_engine_fixtures() if item.id == "pet-dog-callable-friendly"
        )
        rows = run_engine_audit([fixture], rounds=1, use_ai=False, run_id="judge-test")
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "audit.csv"
            judged = Path(tmpdir) / "audit-judged.csv"
            write_engine_audit_csv(rows, source)
            fieldnames, raw_rows = read_rows(source)
            judged_rows = [judge_row(dict(row)) for row in raw_rows]
            write_rows(judged, fieldnames, judged_rows)
            with judged.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                output_rows = list(reader)

        self.assertEqual(len(output_rows), 1)
        self.assertIn("judge_score", output_rows[0])
        self.assertIn("judge_notes", output_rows[0])
        self.assertTrue(output_rows[0]["judge_score"])


if __name__ == "__main__":
    unittest.main()
