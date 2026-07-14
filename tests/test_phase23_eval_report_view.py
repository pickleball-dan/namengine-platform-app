import os
import tempfile
import unittest

from app import create_app


class PhaseTwentyThreeEvalReportViewTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "test.sqlite3")
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        self.tempdir.cleanup()

    def test_eval_report_renders_fixture_summary_and_contrasts(self):
        response = self.client.get("/dev/eval-report")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Taste Engine Eval Report", body)
        self.assertIn("Fixture count", body)
        self.assertIn("baby-classic-soft-familiar", body)
        self.assertIn("baby-rare-strong-distinctive", body)
        self.assertIn("Contrast groups", body)
        self.assertIn("Final names", body)

    def test_eval_report_limit_keeps_ai_smoke_route_safe(self):
        response = self.client.get("/dev/eval-report?limit=2")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Limit", body)
        self.assertIn("baby-classic-soft-familiar", body)
        self.assertIn("baby-rare-strong-distinctive", body)
        self.assertNotIn("baby-literary-nature", body)


if __name__ == "__main__":
    unittest.main()
