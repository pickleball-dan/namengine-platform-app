import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app


class OpenAITelemetryEndpointTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.telemetry_path = os.path.join(self.tempdir.name, "telemetry.jsonl")
        self.environment = patch.dict(
            os.environ,
            {
                "MISSION_CONTROL_TELEMETRY_TOKEN": "test-service-secret",
                "NAMENGINE_OPENAI_TELEMETRY_PATH": self.telemetry_path,
            },
        )
        self.environment.start()
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.environment.stop()
        self.tempdir.cleanup()

    def _headers(self, token="test-service-secret"):
        return {"Authorization": f"Bearer {token}"}

    def test_rejects_missing_and_invalid_authentication(self):
        self.assertEqual(
            self.client.get("/api/internal/mission-control/openai-usage").status_code,
            401,
        )
        response = self.client.get(
            "/api/internal/mission-control/openai-usage",
            headers=self._headers("wrong-secret"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "unauthorized"})

    def test_returns_aggregate_data_for_authenticated_request(self):
        with open(self.telemetry_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "timestamp": "2026-07-20T10:00:00Z",
                "request_type": "responses.create",
                "model": "gpt-4.1-mini",
                "latency_ms": 125,
                "success": True,
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            }) + "\n")

        response = self.client.get(
            "/api/internal/mission-control/openai-usage?start=2026-07-20&end=2026-07-20",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["summary"]["request_count"], 1)
        self.assertNotIn("events", response.get_json())
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_rejects_unknown_repeated_and_unbounded_queries(self):
        unknown = self.client.get(
            "/api/internal/mission-control/openai-usage?path=anything",
            headers=self._headers(),
        )
        repeated = self.client.get(
            "/api/internal/mission-control/openai-usage?model=a&model=b",
            headers=self._headers(),
        )
        unbounded = self.client.get(
            "/api/internal/mission-control/openai-usage?start=2026-01-01&end=2026-07-20",
            headers=self._headers(),
        )

        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(repeated.status_code, 400)
        self.assertEqual(unbounded.status_code, 400)

    def test_missing_server_secret_fails_closed(self):
        os.environ.pop("MISSION_CONTROL_TELEMETRY_TOKEN")
        response = self.client.get(
            "/api/internal/mission-control/openai-usage",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json(), {"error": "telemetry_unavailable"})


if __name__ == "__main__":
    unittest.main()
