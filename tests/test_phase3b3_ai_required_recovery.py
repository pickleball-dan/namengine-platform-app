import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as platform_app
import namengine.core.model_router as model_router
from access_helpers import csrf_token, unlock_beta_access
from namengine.core import get_failed_generation_audits
from namengine.core.ai_generation import AIGenerationError
from namengine.core.briefs import build_brief
from namengine.core.generation import generate_fallback_names, generate_names
from namengine.core.reactions import build_reaction
from namengine.core.schemas import (
    GenerationAccessTier,
    GenerationContext,
    GenerationEnvironment,
    GenerationPurpose,
    NameResult,
    ValidationResult,
    ValidationStatus,
)
from namengine.core.storage import get_magic_links_by_email, get_session_snapshot, save_reaction, save_session
from namengine.verticals import get_vertical


def _ai_names(vertical_slug: str = "baby") -> list[NameResult]:
    return [
        NameResult(
            id=f"{vertical_slug}-{index}",
            name=name,
            slug=name.lower().replace(" ", "-"),
            pronunciation=name,
            tagline="A thoughtful candidate.",
            meaning="A suitable name.",
            why_this_name="Fits the saved direction.",
            fit_note="Strong fit for this brief.",
            risks=["Review before committing."],
            tags=["ai"],
            scores={"fit": 0.9, "usability": 0.9, "distinctiveness": 0.75},
            validation=[
                ValidationResult(
                    module="test_validation",
                    status=ValidationStatus.PASS,
                    label="Valid",
                    message="Valid test result.",
                )
            ],
            metadata={"source": "openai", "provider": "openai"},
        )
        for index, name in enumerate(
            ["Eleanor", "Clara", "Alice", "Lucy", "Julia", "Celia", "Eliza", "Nina"],
            start=1,
        )
    ]


def _session_id_from_recovery_page(body: str) -> str:
    match = re.search(r'name="session_id" value="([^"]+)"', body)
    if not match:
        raise AssertionError("recovery page did not include a session_id")
    return match.group(1)


class PhaseThreeBThreeAiRequiredRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_env = os.environ.get("NAMENGINE_ENVIRONMENT")
        self.previous_ai_verticals = os.environ.get("NAMENGINE_AI_PRIMARY_VERTICALS")
        os.environ["NAMENGINE_DB_PATH"] = str(Path(self.tempdir.name) / "namengine.sqlite3")
        os.environ["NAMENGINE_ENVIRONMENT"] = "production"
        os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = "baby,pet,business,boat"
        self.app = platform_app.create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        self.tempdir.cleanup()
        self._restore_env("NAMENGINE_DB_PATH", self.previous_db)
        self._restore_env("NAMENGINE_ENVIRONMENT", self.previous_env)
        self._restore_env("NAMENGINE_AI_PRIMARY_VERTICALS", self.previous_ai_verticals)

    def _restore_env(self, key: str, value: str | None) -> None:
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    def test_free_first_list_failure_preserves_session_and_blocks_fallback(self):
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            model_router, "_openai_provider", side_effect=AIGenerationError("request timed out")
        ), patch.object(model_router, "_fallback_provider", wraps=model_router._fallback_provider) as fallback:
            response = self.client.post(
                "/baby/results",
                data={"gender": "Girl", "style": "Classic", "sound": "Soft"},
            )

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 503)
        self.assertIn("We want to get this right.", body)
        self.assertIn("Email me a link", body)
        fallback.assert_not_called()
        session_id = _session_id_from_recovery_page(body)
        snapshot = get_session_snapshot(session_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["session"]["vertical"], "baby")
        self.assertEqual(snapshot["results"], [])
        failures = get_failed_generation_audits("baby")
        self.assertEqual(failures[0]["session_id"], session_id)
        self.assertEqual(failures[0]["generation_purpose"], "first_list")

    def test_try_again_uses_preserved_session_and_openai_only(self):
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            model_router, "_openai_provider", side_effect=AIGenerationError("request timed out")
        ):
            failed = self.client.post(
                "/baby/results",
                data={"gender": "Girl", "style": "Classic", "sound": "Soft"},
            )
        session_id = _session_id_from_recovery_page(failed.get_data(as_text=True))

        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            platform_app, "generate_with_router", return_value=_ai_names("baby")
        ) as generate:
            retry = self.client.post(
                f"/results/session/{session_id}/retry",
                data={"csrf_token": csrf_token(self.client)},
            )

        self.assertEqual(retry.status_code, 302)
        self.assertIn(f"/results/session/{session_id}", retry.headers["Location"])
        call = generate.call_args.kwargs
        self.assertEqual(call["providers"], [platform_app.ModelProvider.OPENAI])
        self.assertFalse(call["fallback_on_provider_error"])
        snapshot = get_session_snapshot(session_id)
        self.assertEqual(len(snapshot["results"]), 8)

    def test_magic_link_recovery_reuses_existing_token_and_does_not_grant_paid_access(self):
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            model_router, "_openai_provider", side_effect=AIGenerationError("request timed out")
        ):
            failed = self.client.post(
                "/baby/results",
                data={"gender": "Girl", "style": "Classic", "sound": "Soft"},
            )
        session_id = _session_id_from_recovery_page(failed.get_data(as_text=True))

        with patch.object(platform_app, "send_magic_link") as send:
            response = self.client.post(
                "/api/save-progress",
                json={"session_id": session_id, "email": "tester@example.com"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(send.call_args.kwargs["recovery"])
        token = get_magic_links_by_email("tester@example.com", "baby")[0]["token"]
        resumed = self.client.get(f"/continue/{token}")
        self.assertEqual(resumed.status_code, 302)
        self.assertIn(f"/results/session/{session_id}", resumed.headers["Location"])
        self.assertIsNone(self.client.get_cookie(platform_app.beta_unlock_cookie_name(get_vertical("baby"))))

    def test_pet_original_and_boat_fail_closed_without_local_fallback(self):
        for vertical_slug, source in (
            ("pet", {"pet_type": "Dog", "vibe": "Gentle", "style": "Warm"}),
            ("boat", {"vessel_type": "Sailboat", "usage": "Coastal weekends", "style": "Classic"}),
        ):
            with self.subTest(vertical=vertical_slug), patch.object(
                platform_app, "is_ai_generation_configured", return_value=True
            ), patch.object(
                model_router, "_openai_provider", side_effect=AIGenerationError("request timed out")
            ), patch.object(model_router, "_fallback_provider", wraps=model_router._fallback_provider) as fallback:
                vertical = get_vertical(vertical_slug)
                brief = build_brief(vertical, source)
                context = GenerationContext(
                    purpose=GenerationPurpose.FIRST_LIST,
                    access_tier=GenerationAccessTier.FREE,
                    environment=GenerationEnvironment.PRODUCTION,
                )
                with self.assertRaises(platform_app.NameGenerationUnavailable):
                    platform_app._generate_names_for_route(
                        vertical,
                        brief,
                        generation_context=context,
                        session_id=f"{vertical_slug}-failed",
                    )
                fallback.assert_not_called()

    def test_cached_marked_fallback_is_not_valid_customer_ai_output(self):
        for vertical_slug in ("baby", "pet", "business", "boat"):
            with self.subTest(vertical=vertical_slug):
                vertical = get_vertical(vertical_slug)
                brief = build_brief(vertical, {"style": "Classic", "pet_type": "Dog"})
                names = generate_fallback_names(vertical, brief)
                for name in names:
                    name.metadata["ai_primary_requested"] = True
                    name.metadata["ai_primary_fallback"] = True
                self.assertFalse(platform_app._cached_names_match_current_rules(vertical, brief, names))

    def test_internal_generation_can_still_use_explicit_fallback(self):
        vertical = get_vertical("pet")
        brief = build_brief(vertical, {"pet_type": "Dog", "vibe": "Playful"})
        names = generate_names(vertical, brief, use_ai=False)
        self.assertTrue(names)
        self.assertEqual(names[0].metadata.get("provider"), "fallback")

    def test_paid_refinement_failure_preserves_child_session_and_requires_paid_retry(self):
        vertical = get_vertical("baby")
        parent_id = "baby-paid-parent"
        brief = build_brief(vertical, {"gender": "Girl", "style": "Classic", "sound": "Soft"})
        save_session(parent_id, vertical.slug, brief, _ai_names("baby"))
        for index, value in enumerate(("love", "maybe", "no"), start=1):
            save_reaction(build_reaction(parent_id, f"baby-{index}", value))

        unlock_beta_access(self.client, "baby")
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            model_router, "_openai_provider", side_effect=AIGenerationError("request timed out")
        ), patch.object(model_router, "_fallback_provider", wraps=model_router._fallback_provider) as fallback:
            response = self.client.post(
                "/refine",
                data={"session_id": parent_id, "instruction": "warmer", "csrf_token": csrf_token(self.client)},
            )

        self.assertEqual(response.status_code, 503)
        fallback.assert_not_called()
        child_id = f"{parent_id}-r2"
        child = get_session_snapshot(child_id)
        self.assertIsNotNone(child)
        self.assertEqual(child["results"], [])

        fresh_client = self.app.test_client()
        fresh_client.get(f"/results/session/{child_id}")
        retry = fresh_client.post(
            f"/results/session/{child_id}/retry",
            data={"csrf_token": csrf_token(fresh_client)},
        )
        self.assertEqual(retry.status_code, 302)
        self.assertIn("/baby/access", retry.headers["Location"])


if __name__ == "__main__":
    unittest.main()
