import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app


class PhaseTwentyThreeEvalReportViewTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_engine_audit_enabled = os.environ.get("NAMENGINE_ENABLE_ENGINE_AUDIT")
        os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = "1"
        self.previous_telemetry_token = os.environ.get("NAMENGINE_TELEMETRY_TOKEN")
        os.environ["NAMENGINE_TELEMETRY_TOKEN"] = "test-telemetry-token"
        self.auth_headers = {"Authorization": "Bearer test-telemetry-token"}
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_engine_audit_enabled is None:
            os.environ.pop("NAMENGINE_ENABLE_ENGINE_AUDIT", None)
        else:
            os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = self.previous_engine_audit_enabled
        if self.previous_telemetry_token is None:
            os.environ.pop("NAMENGINE_TELEMETRY_TOKEN", None)
        else:
            os.environ["NAMENGINE_TELEMETRY_TOKEN"] = self.previous_telemetry_token
        self.tempdir.cleanup()

    def test_eval_report_returns_404_when_engine_audit_disabled(self):
        os.environ.pop("NAMENGINE_ENABLE_ENGINE_AUDIT", None)
        app = create_app()
        app.testing = True
        client = app.test_client()

        response = client.get("/dev/eval-report", headers=self.auth_headers)

        self.assertEqual(response.status_code, 404)

    def test_eval_report_returns_404_without_valid_token(self):
        response = self.client.get("/dev/eval-report")
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            "/dev/eval-report", headers={"Authorization": "Bearer wrong-token"}
        )
        self.assertEqual(response.status_code, 404)

    def test_eval_report_renders_fixture_summary_and_contrasts(self):
        response = self.client.get("/dev/eval-report", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Taste Engine Eval Report", body)
        self.assertIn("Fixture count", body)
        self.assertIn("baby-classic-soft-familiar", body)
        self.assertIn("baby-rare-strong-distinctive", body)
        self.assertIn("Contrast groups", body)
        self.assertIn("Final names", body)

    def test_eval_report_defaults_to_fallback_engine(self):
        with patch("app.run_taste_engine_fixture_set", return_value=[]) as run_fixture_set:
            response = self.client.get("/dev/eval-report", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(run_fixture_set.call_args.kwargs["use_ai"], False)
        self.assertIn("Fallback", response.get_data(as_text=True))

    def test_eval_report_allows_explicit_ai_opt_in(self):
        with patch("app.run_taste_engine_fixture_set", return_value=[]) as run_fixture_set:
            response = self.client.get("/dev/eval-report?ai=1", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(run_fixture_set.call_args.kwargs["use_ai"], True)

    def test_eval_report_limit_keeps_ai_smoke_route_safe(self):
        response = self.client.get("/dev/eval-report?limit=2", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Limit", body)
        self.assertIn("baby-classic-soft-familiar", body)
        self.assertIn("baby-rare-strong-distinctive", body)
        self.assertNotIn("baby-literary-nature", body)


if __name__ == "__main__":
    unittest.main()
