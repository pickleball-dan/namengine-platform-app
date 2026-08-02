import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from app import create_app
from namengine.core import build_brief, generate_names, save_failed_generation_audit, save_session
from namengine.core.mission_control_telemetry import build_openai_usage_report
from namengine.verticals import get_vertical


class MissionControlTelemetryV1Test(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_token = os.environ.get("NAMENGINE_TELEMETRY_TOKEN")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "telemetry.sqlite3")
        os.environ["NAMENGINE_TELEMETRY_TOKEN"] = "test-telemetry-token"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_token is None:
            os.environ.pop("NAMENGINE_TELEMETRY_TOKEN", None)
        else:
            os.environ["NAMENGINE_TELEMETRY_TOKEN"] = self.previous_token
        self.tempdir.cleanup()

    def _seed_openai_session(self):
        vertical = get_vertical("baby")
        brief = build_brief(vertical, {"gender": "Girl", "style": "Classic"})
        names = generate_names(vertical, brief, use_ai=False)[:2]
        for name in names:
            name.metadata.update(
                {
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "prompt_version": "namengine-baby-quality-v1",
                    "ai_calls": [
                        {
                            "stage": "taste_interpreter_v1",
                            "model": "gpt-4.1-mini",
                            "latency_ms": 100,
                            "usage": {"input_tokens": 100, "output_tokens": 25, "total_tokens": 125},
                        },
                        {
                            "stage": "candidate_generator_v1",
                            "model": "gpt-4.1-mini",
                            "latency_ms": 200,
                            "usage": {"input_tokens": 200, "output_tokens": 50, "total_tokens": 250},
                        },
                    ],
                }
            )
        save_session("baby-telemetry-session", "baby", brief, names)

    def _seed_business_openai_session(self):
        vertical = get_vertical("business")
        brief = build_brief(
            vertical,
            {
                "business_description": "Operations support for growing service businesses",
                "industry": "Operations consulting",
                "audience": "B2B buyers",
                "style": "Clear and credible",
            },
        )
        names = generate_names(vertical, brief, use_ai=False)[:2]
        for name in names:
            name.metadata.update(
                {
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "prompt_version": "namengine-business-quality-v1",
                    "ai_calls": [
                        {
                            "stage": "business_candidate_generator_v1",
                            "model": "gpt-4.1-mini",
                            "latency_ms": 150,
                            "usage": {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150},
                        }
                    ],
                }
            )
        save_session("business-telemetry-session", "business", brief, names)

    def test_usage_report_aggregates_spend_tokens_and_requests(self):
        self._seed_openai_session()

        report = build_openai_usage_report()

        self.assertEqual(report["summary"]["request_count"], 2)
        self.assertEqual(report["summary"]["success_count"], 2)
        self.assertEqual(report["summary"]["input_tokens"], 300)
        self.assertEqual(report["summary"]["output_tokens"], 75)
        self.assertEqual(report["summary"]["total_tokens"], 375)
        self.assertEqual(report["summary"]["generated_name_count"], 2)
        self.assertAlmostEqual(report["summary"]["estimated_spend_usd"], 0.00024, places=6)
        self.assertEqual(report["requests_by_model"][0]["model"], "gpt-4.1-mini")
        self.assertEqual(report["requests_by_session"][0]["session_id"], "baby-telemetry-session")
        self.assertEqual(report["requests_by_session"][0]["request_count"], 2)
        self.assertEqual(report["requests_by_session"][0]["input_tokens"], 300)
        self.assertEqual(report["requests_by_session"][0]["output_tokens"], 75)
        self.assertEqual(report["requests_by_session"][0]["total_tokens"], 375)
        self.assertAlmostEqual(
            report["requests_by_session"][0]["estimated_spend_usd"],
            0.00024,
            places=6,
        )
        self.assertEqual(report["requests_by_vertical"][0]["vertical"], "baby")
        self.assertTrue(report["requests_by_day"])

    def test_usage_report_filters_and_groups_by_vertical(self):
        self._seed_openai_session()
        self._seed_business_openai_session()

        report = build_openai_usage_report(vertical="business")

        self.assertEqual(report["summary"]["request_count"], 1)
        self.assertEqual(report["summary"]["input_tokens"], 120)
        self.assertEqual(report["summary"]["output_tokens"], 30)
        self.assertEqual(report["requests_by_vertical"], [
            {
                "vertical": "business",
                "request_count": 1,
                "success_count": 1,
                "failure_count": 0,
                "success_rate": 100.0,
                "input_tokens": 120,
                "output_tokens": 30,
                "total_tokens": 150,
                "average_latency_ms": 150.0,
                "maximum_latency_ms": 150,
                "image_generation_count": 0,
                "requests_missing_token_usage": 0,
                "estimated_spend_usd": 0.000096,
                "generated_name_count": 2,
            }
        ])

    def test_endpoint_filters_by_vertical(self):
        self._seed_openai_session()
        self._seed_business_openai_session()

        response = self.client.get(
            "/api/internal/mission-control/openai-usage?vertical=business",
            headers={"Authorization": "Bearer test-telemetry-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["summary"]["request_count"], 1)
        self.assertEqual(payload["requests_by_vertical"][0]["vertical"], "business")
        self.assertEqual(payload["requests_by_session"][0]["session_id"], "business-telemetry-session")

    def test_internal_endpoint_requires_bearer_token(self):
        self._seed_openai_session()

        self.assertEqual(self.client.get("/api/internal/mission-control/openai-usage").status_code, 401)
        self.assertEqual(
            self.client.get(
                "/api/internal/mission-control/openai-usage",
                headers={"Authorization": "Bearer wrong-token"},
            ).status_code,
            401,
        )

        response = self.client.get(
            "/api/internal/mission-control/openai-usage",
            headers={"Authorization": "Bearer test-telemetry-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["summary"]["request_count"], 2)
        self.assertIn("estimated_spend_usd", payload["summary"])

    def test_endpoint_filters_by_date_and_success(self):
        self._seed_openai_session()
        save_failed_generation_audit(
            vertical="baby",
            provider="openai",
            model="gpt-4.1-mini",
            prompt_version="namengine-baby-quality-v1",
            latency_ms=300,
            customer_intake={},
            exception_type="RuntimeError",
            safe_error_message="safe",
        )
        start = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        response = self.client.get(
            f"/api/internal/mission-control/openai-usage?start={start}&end={end}&success=false",
            headers={"Authorization": "Bearer test-telemetry-token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["summary"]["request_count"], 1)
        self.assertEqual(payload["summary"]["failure_count"], 1)
        self.assertEqual(payload["failures_by_error_type"][0]["error_type"], "RuntimeError")

    def test_invalid_boolean_query_returns_400(self):
        response = self.client.get(
            "/api/internal/mission-control/openai-usage?success=maybe",
            headers={"Authorization": "Bearer test-telemetry-token"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
