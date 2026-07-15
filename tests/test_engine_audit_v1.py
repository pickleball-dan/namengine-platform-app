import os
import tempfile
import unittest
from unittest.mock import patch

import app as platform_app
from app import create_app
from namengine.core import (
    build_brief,
    build_reaction,
    generate_names,
    get_failed_generation_audits,
    get_recent_audit_sessions,
    save_chosen_name,
    save_reaction,
    save_session,
)
from namengine.verticals import get_vertical


class EngineAuditV1Test(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "audit.sqlite3")
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        self.tempdir.cleanup()

    def _seed_session(self, session_id="baby-audit-session", vertical_slug="baby"):
        vertical = get_vertical(vertical_slug)
        source = {"gender": "Girl", "style": "Playful"} if vertical_slug == "baby" else {
            "pet_type": "Dog",
            "style": "Warm",
        }
        brief = build_brief(vertical, source)
        names = generate_names(vertical, brief, use_ai=False)[:2]
        for name in names:
            name.metadata.update(
                {
                    "provider": "openai",
                    "model": "audit-test-model",
                    "prompt_version": "audit-prompt-v1",
                    "ai_calls": [{"latency_ms": 37, "usage": {"input_tokens": 10}}],
                }
            )
        save_session(session_id, vertical_slug, brief, names)
        return names

    def test_audit_index_defaults_to_baby_and_lists_session_summary(self):
        names = self._seed_session()
        self._seed_session("pet-audit-session", "pet")
        save_reaction(build_reaction("baby-audit-session", names[0].id, "love"))
        save_reaction(build_reaction("baby-audit-session", names[1].id, "maybe"))
        save_chosen_name("baby-audit-session", names[0].id)

        response = self.client.get("/dev/engine-audit")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Recent Engine Audits", body)
        self.assertIn("/dev/engine-audit/baby-audit-session", body)
        self.assertNotIn("pet-audit-session", body)
        self.assertIn("audit-test-model", body)
        self.assertIn("audit-prompt-v1", body)
        self.assertIn("37 ms", body)
        self.assertIn("Chosen:", body)

    def test_audit_index_accepts_vertical_and_limit(self):
        self._seed_session("pet-audit-a", "pet")
        self._seed_session("pet-audit-b", "pet")

        response = self.client.get("/dev/engine-audit?vertical=pet&limit=1")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertEqual(body.count("/dev/engine-audit/pet-audit-"), 1)
        self.assertIn('value="1"', body)

    def test_successful_session_summary_has_required_counts(self):
        names = self._seed_session()
        save_reaction(build_reaction("baby-audit-session", names[0].id, "no"))

        summary = get_recent_audit_sessions("baby", 10)[0]

        self.assertEqual(summary["session_id"], "baby-audit-session")
        self.assertTrue(summary["timestamp"])
        self.assertEqual(summary["round_number"], 1)
        self.assertIsNone(summary["parent_session_id"])
        self.assertEqual(summary["names_returned"], 2)
        self.assertEqual(summary["no_count"], 1)
        self.assertEqual(summary["love_count"], 0)
        self.assertEqual(summary["provider"], "openai")
        self.assertEqual(summary["model"], "audit-test-model")
        self.assertEqual(summary["prompt_version"], "audit-prompt-v1")
        self.assertEqual(summary["total_latency_ms"], 37)
        self.assertEqual(summary["chosen_count"], 0)

    def test_audit_detail_is_preserved_and_redacts_secret_shaped_metadata(self):
        names = self._seed_session()
        names[0].metadata["api_key"] = "should-never-render"
        names[0].metadata["OPENAI_API_KEY"] = "also-never-render"
        names[0].metadata["private_key"] = "private-key-never-renders"
        names[0].metadata["input_tokens"] = 42
        brief = build_brief(get_vertical("baby"), {"gender": "Girl", "style": "Playful"})
        save_session("baby-audit-session", "baby", brief, names)
        save_chosen_name("baby-audit-session", names[0].id)

        response = self.client.get("/dev/engine-audit/baby-audit-session")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Engine Audit", body)
        self.assertIn("Recent audits", body)
        self.assertIn("Chosen name", body)
        self.assertIn("[redacted]", body)
        self.assertNotIn("should-never-render", body)
        self.assertNotIn("also-never-render", body)
        self.assertNotIn("private-key-never-renders", body)
        self.assertIn("input_tokens", body)

    def test_failed_generation_is_durably_captured_with_safe_message(self):
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            platform_app,
            "generate_with_router",
            side_effect=RuntimeError("provider secret and traceback detail"),
        ), patch.dict(os.environ, {"NAMENGINE_AI_PRIMARY_VERTICALS": "baby"}):
            response = self.client.get("/baby/results?gender=Girl&style=Playful")

        self.assertEqual(response.status_code, 503)
        failures = get_failed_generation_audits("baby")
        self.assertEqual(len(failures), 1)
        failure = failures[0]
        self.assertEqual(failure["vertical"], "baby")
        self.assertEqual(failure["provider"], "openai")
        self.assertEqual(failure["exception_type"], "RuntimeError")
        self.assertEqual(failure["customer_intake"]["inputs"]["gender"], "Girl")
        self.assertNotIn("provider secret", failure["safe_error_message"])

        audit_response = self.client.get("/dev/engine-audit")
        body = audit_response.get_data(as_text=True)
        self.assertIn("Failed generations", body)
        self.assertIn("RuntimeError", body)
        self.assertNotIn("provider secret", body)
        self.assertNotIn("traceback detail", body)


if __name__ == "__main__":
    unittest.main()
