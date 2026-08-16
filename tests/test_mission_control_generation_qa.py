import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app


class MissionControlGenerationQATest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_token = os.environ.get("NAMENGINE_TELEMETRY_TOKEN")
        self.previous_engine_audit_enabled = os.environ.get("NAMENGINE_ENABLE_ENGINE_AUDIT")
        self.previous_output_root = os.environ.get("NAMENGINE_GENERATION_QA_OUTPUT_ROOT")
        os.environ["NAMENGINE_TELEMETRY_TOKEN"] = "test-telemetry-token"
        os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = "1"
        os.environ["NAMENGINE_GENERATION_QA_OUTPUT_ROOT"] = os.path.join(self.tempdir.name, "generation-runs")
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        self.auth_headers = {"Authorization": "Bearer test-telemetry-token"}

    def tearDown(self):
        if self.previous_token is None:
            os.environ.pop("NAMENGINE_TELEMETRY_TOKEN", None)
        else:
            os.environ["NAMENGINE_TELEMETRY_TOKEN"] = self.previous_token
        if self.previous_engine_audit_enabled is None:
            os.environ.pop("NAMENGINE_ENABLE_ENGINE_AUDIT", None)
        else:
            os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = self.previous_engine_audit_enabled
        if self.previous_output_root is None:
            os.environ.pop("NAMENGINE_GENERATION_QA_OUTPUT_ROOT", None)
        else:
            os.environ["NAMENGINE_GENERATION_QA_OUTPUT_ROOT"] = self.previous_output_root
        self.tempdir.cleanup()

    def test_generation_qa_status_requires_bearer_token(self):
        self.assertEqual(self.client.get("/api/internal/mission-control/generation-qa").status_code, 401)
        self.assertEqual(
            self.client.get(
                "/api/internal/mission-control/generation-qa",
                headers={"Authorization": "Bearer wrong-token"},
            ).status_code,
            401,
        )

    def test_generation_qa_status_reports_latest_summary_when_available(self):
        latest = Path(os.environ["NAMENGINE_GENERATION_QA_OUTPUT_ROOT"]) / "latest"
        latest.mkdir(parents=True)
        summary = {
            "schema_version": "generation-simulator-v1",
            "run_id": "generation-qa-test",
            "scenario_count": 3,
            "round_count": 3,
            "anomaly_count": 0,
        }
        (latest / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

        response = self.client.get("/api/internal/mission-control/generation-qa", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["summary"]["run_id"], "generation-qa-test")
        self.assertIn("summary.json", payload["summary_path"])
        self.assertIn("report.md", payload["report_path"])
        self.assertIn("results.json", payload["results_path"])

    def test_generation_qa_report_returns_latest_report_and_results(self):
        latest = Path(os.environ["NAMENGINE_GENERATION_QA_OUTPUT_ROOT"]) / "latest"
        latest.mkdir(parents=True)
        summary = {"schema_version": "generation-simulator-v1", "run_id": "generation-qa-test"}
        results = [{"id": "baby-test", "rounds": []}]
        (latest / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (latest / "report.md").write_text("# QA report", encoding="utf-8")
        (latest / "results.json").write_text(json.dumps(results), encoding="utf-8")

        response = self.client.get("/api/internal/mission-control/generation-qa/report", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["summary"]["run_id"], "generation-qa-test")
        self.assertEqual(payload["report_markdown"], "# QA report")
        self.assertEqual(payload["results"], results)

    def test_generation_qa_run_triggers_fast_fallback_and_writes_artifacts(self):
        response = self.client.post(
            "/api/internal/mission-control/generation-qa/run",
            headers=self.auth_headers,
            json={"mode": "fast"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "completed")
        summary = payload["summary"]
        self.assertEqual(summary["mode"], "fallback")
        self.assertEqual(summary["scenario_count"], 3)
        self.assertEqual(summary["anomaly_count"], 0)
        self.assertTrue(Path(summary["summary_path"]).exists())
        self.assertTrue(Path(summary["report_path"]).exists())
        self.assertTrue(Path(summary["results_path"]).exists())
        latest = Path(os.environ["NAMENGINE_GENERATION_QA_OUTPUT_ROOT"]) / "latest"
        self.assertTrue((latest / "results.json").exists())
        self.assertEqual(payload["results_path"], summary["results_path"])

    def test_generation_qa_run_validates_mode_and_ai_confirmation(self):
        bad_mode = self.client.post(
            "/api/internal/mission-control/generation-qa/run",
            headers=self.auth_headers,
            json={"mode": "weekly"},
        )
        self.assertEqual(bad_mode.status_code, 400)
        self.assertEqual(bad_mode.get_json()["error"], "invalid_mode")

        ai_without_confirmation = self.client.post(
            "/api/internal/mission-control/generation-qa/run",
            headers=self.auth_headers,
            json={"mode": "fast", "use_ai": True},
        )
        self.assertEqual(ai_without_confirmation.status_code, 400)
        self.assertEqual(ai_without_confirmation.get_json()["error"], "ai_confirmation_required")

    def test_generation_qa_control_page_is_internal_and_protected(self):
        response = self.client.get("/dev/generation-qa")
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/dev/generation-qa", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Generation QA", body)
        self.assertIn("Protected API actions", body)

    def test_generation_qa_control_page_requires_engine_audit_flag(self):
        os.environ.pop("NAMENGINE_ENABLE_ENGINE_AUDIT", None)
        app = create_app()
        app.testing = True
        client = app.test_client()

        response = client.get("/dev/generation-qa", headers=self.auth_headers)

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
