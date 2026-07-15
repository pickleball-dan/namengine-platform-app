import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as platform_app
from app import create_app
from namengine.core.briefs import build_brief
from namengine.core.schemas import NameResult, ValidationResult, ValidationStatus
from namengine.core.storage import get_session_snapshot, save_session
from namengine.verticals import get_vertical


def _validation():
    return [
        ValidationResult(
            module="baby_gender_direction",
            status=ValidationStatus.PASS,
            label="Gender direction",
            message="Compatible with the requested Girl direction.",
        )
    ]


def _fallback_names():
    return [
        NameResult(
            id="baby-1",
            name="Zahara",
            slug="zahara",
            validation=_validation(),
            metadata={"source": "baby_fallback", "provider": "fallback"},
        )
    ]


def _openai_names():
    return [
        NameResult(
            id="baby-1",
            name="Himari",
            slug="himari",
            validation=_validation(),
            metadata={"source": "openai", "provider": "openai"},
        )
    ]


class PhaseThirtySevenBabySessionStaleFallbackBlockTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_ai_verticals = os.environ.get("NAMENGINE_AI_PRIMARY_VERTICALS")
        os.environ["NAMENGINE_DB_PATH"] = str(Path(self.tempdir.name) / "namengine.sqlite3")
        os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = "baby"
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.tempdir.cleanup()
        if self.previous_db is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db
        if self.previous_ai_verticals is None:
            os.environ.pop("NAMENGINE_AI_PRIMARY_VERTICALS", None)
        else:
            os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = self.previous_ai_verticals

    def test_old_baby_session_with_fallback_names_is_regenerated_not_displayed(self):
        vertical = get_vertical("baby")
        brief = build_brief(vertical, {"gender": "Girl", "style": "Nature-inspired"})
        session_id = "baby-stale-fallback-session"
        save_session(session_id, vertical.slug, brief, _fallback_names())

        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            platform_app, "generate_with_router", return_value=_openai_names()
        ) as mocked_generate:
            response = self.client.get(f"/results/session/{session_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Himari", body)
        self.assertNotIn("Zahara", body)
        self.assertEqual(mocked_generate.call_args.kwargs["providers"], [platform_app.ModelProvider.OPENAI])
        snapshot = get_session_snapshot(session_id)
        self.assertEqual(snapshot["results"][0]["name"], "Himari")


if __name__ == "__main__":
    unittest.main()
