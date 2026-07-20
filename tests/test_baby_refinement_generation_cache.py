import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as platform_app
import namengine.core.model_router as model_router
from app import create_app
from namengine.core.ai_generation import AIGenerationError
from namengine.core.briefs import build_brief
from namengine.core.reactions import build_reaction
from namengine.core.schemas import NameResult, ValidationResult, ValidationStatus
from namengine.core.storage import get_session_snapshot, save_reaction, save_session
from namengine.verticals import get_vertical


def _baby_validation():
    return [
        ValidationResult(
            module="baby_gender_direction",
            status=ValidationStatus.PASS,
            label="Gender direction",
            message="Compatible with the requested Girl direction.",
        )
    ]


def _ai_names(prefix="round"):
    return [
        NameResult(
            id=f"baby-{index}",
            name=name,
            slug=name.lower(),
            pronunciation=name,
            tagline="A thoughtful candidate.",
            meaning="A well-established given name.",
            why_this_name="Fits the requested classic, soft direction.",
            fit_note="Balances warmth and everyday usability.",
            risks=["Review family and cultural fit."],
            tags=["classic", "soft"],
            scores={"fit": 0.9, "usability": 0.9, "distinctiveness": 0.75},
            validation=_baby_validation(),
            metadata={"source": "openai", "provider": "openai", "test_round": prefix},
        )
        for index, name in enumerate(
            ["Eleanor", "Clara", "Alice", "Lucy", "Julia", "Celia", "Eliza", "Nina"],
            start=1,
        )
    ]


class BabyRefinementGenerationCacheTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_ai_verticals = os.environ.get("NAMENGINE_AI_PRIMARY_VERTICALS")
        os.environ["NAMENGINE_DB_PATH"] = str(Path(self.tempdir.name) / "namengine.sqlite3")
        os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = "baby"
        self.app = create_app()
        self.client = self.app.test_client()
        self.vertical = get_vertical("baby")

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

    def _seed_round_one(self):
        session_id = "baby-refinement-parent"
        brief = build_brief(self.vertical, {"gender": "Girl", "style": "Classic", "sound": "Soft"})
        save_session(session_id, self.vertical.slug, brief, _ai_names("one"))
        for index, value in enumerate(("love", "maybe", "no"), start=1):
            save_reaction(build_reaction(session_id, f"baby-{index}", value))
        return session_id

    def test_refinement_post_generates_once_and_redirected_get_reuses_valid_saved_names(self):
        parent_id = self._seed_round_one()
        generated = _ai_names("two")

        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            platform_app, "generate_with_router", return_value=generated
        ) as generate:
            response = self.client.post(
                "/refine",
                data={"session_id": parent_id, "instruction": "a little lighter"},
                headers={"X-NamEngine-Progress": "1"},
            )

            self.assertEqual(response.status_code, 302)
            self.assertEqual(generate.call_count, 1)
            call = generate.call_args.kwargs
            self.assertEqual(call["round_number"], 2)
            self.assertEqual(call["providers"], [platform_app.ModelProvider.OPENAI])
            self.assertTrue(call["fallback_on_provider_error"])

            child_id = response.headers["Location"].rsplit("/", 1)[-1]
            snapshot = get_session_snapshot(child_id)
            saved_names = platform_app._names_from_snapshot(snapshot)
            saved_brief = platform_app._brief_from_snapshot(snapshot)
            self.assertTrue(
                platform_app._cached_names_match_current_rules(self.vertical, saved_brief, saved_names)
            )

            generate.reset_mock()
            follow = self.client.get(response.headers["Location"])
            self.assertEqual(follow.status_code, 200)
            generate.assert_not_called()

    def test_refinement_timeout_uses_one_deterministic_fallback_and_get_reuses_it(self):
        parent_id = self._seed_round_one()

        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            model_router, "_openai_provider", side_effect=AIGenerationError("request timed out")
        ) as openai:
            response = self.client.post(
                "/refine",
                data={"session_id": parent_id, "instruction": "keep it classic"},
                headers={"X-NamEngine-Progress": "1"},
            )

            self.assertEqual(response.status_code, 302)
            self.assertEqual(openai.call_count, 1)
            child_id = response.headers["Location"].rsplit("/", 1)[-1]
            snapshot = get_session_snapshot(child_id)
            saved_names = platform_app._names_from_snapshot(snapshot)
            saved_brief = platform_app._brief_from_snapshot(snapshot)
            self.assertTrue(saved_names)
            self.assertTrue(all(name.metadata.get("provider") == "fallback" for name in saved_names))
            self.assertTrue(all(name.metadata.get("ai_primary_fallback") is True for name in saved_names))
            self.assertTrue(
                platform_app._cached_names_match_current_rules(self.vertical, saved_brief, saved_names)
            )
            self.assertFalse(
                platform_app._cached_names_match_current_rules(
                    self.vertical,
                    saved_brief,
                    [_ai_names("mixed")[0], saved_names[0]],
                )
            )

            openai.reset_mock()
            follow = self.client.get(response.headers["Location"])
            self.assertEqual(follow.status_code, 200)
            openai.assert_not_called()

    def test_round_one_keeps_the_existing_ai_primary_route_policy(self):
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            platform_app, "generate_with_router", return_value=_ai_names("one")
        ) as generate:
            response = self.client.post(
                "/baby/results",
                data={"gender": "Girl", "style": "Classic", "sound": "Soft"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(generate.call_count, 1)
        call = generate.call_args.kwargs
        self.assertEqual(call["round_number"], 1)
        self.assertEqual(call["providers"], [platform_app.ModelProvider.OPENAI])
        self.assertTrue(call["fallback_on_provider_error"])


if __name__ == "__main__":
    unittest.main()
