import os
import tempfile
import unittest
from unittest.mock import patch

import app as platform_app
from access_helpers import csrf_token, unlock_beta_access
from app import create_app, make_session_id
from namengine.core import build_brief, build_reaction, save_reaction, save_session
from namengine.core.schemas import (
    GenerationAccessTier,
    GenerationContext,
    GenerationEnvironment,
    GenerationPurpose,
    NameResult,
)
from namengine.verticals import get_vertical


def _fake_names(vertical_slug: str, count: int = 8) -> list[NameResult]:
    return [
        NameResult(
            id=f"{vertical_slug}-{index}",
            name=f"Context {index}",
            slug=f"context-{index}",
            tagline="Generated through the existing route boundary.",
            why_this_name="This test result captures context without changing generation policy.",
            fit_note="Used only for generation-context plumbing tests.",
            metadata={"source": "openai", "provider": "openai"},
        )
        for index in range(1, count + 1)
    ]


class GenerationContextTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "test.sqlite3")
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        self.tempdir.cleanup()

    def test_free_first_list_routes_pass_context_for_all_active_verticals(self):
        captured: dict[str, GenerationContext] = {}

        def capture(vertical, brief, *, generation_context, **kwargs):
            captured[vertical.slug] = generation_context
            return _fake_names(vertical.slug)

        cases = {
            "baby": {"gender": "Girl", "style": "Classic", "sound": "Soft"},
            "pet": {
                "pet_type": "Dog",
                "pet_color": "brown",
                "pet_life_stage": "Young",
                "vibe": "Gentle",
                "style": "Warm",
            },
            "business": {
                "business_description": "A bookkeeping studio",
                "audience": "Local service businesses",
                "style": "Clear and credible",
            },
            "boat": {
                "boat_type": "Sailboat",
                "use": "Weekend adventures",
                "name_type": "Classic nautical",
                "vibe": "Adventurous",
            },
        }

        with patch.object(platform_app, "_generate_names_for_route", side_effect=capture):
            for slug, data in cases.items():
                response = self.client.post(f"/{slug}/results", data=data)
                self.assertEqual(response.status_code, 302, slug)

        self.assertEqual(set(cases), set(captured))
        for context in captured.values():
            self.assertEqual(context.purpose, GenerationPurpose.FIRST_LIST)
            self.assertEqual(context.access_tier, GenerationAccessTier.FREE)
            self.assertEqual(context.environment, GenerationEnvironment.TEST)

    def test_paid_refinement_passes_paid_refinement_context(self):
        vertical = get_vertical("pet")
        brief = build_brief(
            vertical,
            {
                "pet_type": "Dog",
                "pet_color": "brown",
                "pet_life_stage": "Young",
                "vibe": "Gentle",
                "style": "Warm",
            },
        )
        session_id = make_session_id(vertical.slug, b"context-refinement")
        save_session(session_id, vertical.slug, brief, _fake_names(vertical.slug))
        save_reaction(build_reaction(session_id, "pet-1", "love"))
        save_reaction(build_reaction(session_id, "pet-2", "maybe"))
        save_reaction(build_reaction(session_id, "pet-3", "no"))
        unlock_beta_access(self.client, "pet")
        self.client.get(f"/results/session/{session_id}")

        captured: list[GenerationContext] = []

        def capture(vertical, brief, *, generation_context, **kwargs):
            captured.append(generation_context)
            return _fake_names(vertical.slug)

        with patch.object(platform_app, "_generate_names_for_route", side_effect=capture):
            response = self.client.post(
                "/refine",
                data={
                    "session_id": session_id,
                    "instruction": "warmer",
                    "csrf_token": csrf_token(self.client),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].purpose, GenerationPurpose.REFINEMENT)
        self.assertEqual(captured[0].access_tier, GenerationAccessTier.PAID)
        self.assertEqual(captured[0].environment, GenerationEnvironment.TEST)

    def test_internal_qa_context_is_internal_without_using_customer_entitlement(self):
        with self.app.app_context():
            context = platform_app.internal_qa_generation_context()

        self.assertEqual(context.purpose, GenerationPurpose.INTERNAL_QA)
        self.assertEqual(context.access_tier, GenerationAccessTier.INTERNAL)
        self.assertEqual(context.environment, GenerationEnvironment.TEST)

    def test_environment_derives_from_explicit_configuration_and_render_defaults(self):
        with self.app.app_context():
            with patch.dict(os.environ, {"NAMENGINE_ENVIRONMENT": "staging"}, clear=False):
                self.assertEqual(platform_app.generation_environment(), GenerationEnvironment.STAGING)
            with patch.dict(os.environ, {"NAMENGINE_ENVIRONMENT": "production"}, clear=False):
                self.assertEqual(platform_app.generation_environment(), GenerationEnvironment.PRODUCTION)
        with patch.dict(
            os.environ,
            {
                "NAMENGINE_ENVIRONMENT": "",
                "PYTEST_CURRENT_TEST": "",
                "RENDER": "1",
                "RENDER_SERVICE_NAME": "namengine-platform-staging",
            },
            clear=False,
        ):
            self.assertEqual(platform_app.generation_environment(), GenerationEnvironment.STAGING)

    def test_free_context_does_not_encode_lower_quality_or_fallback_permission(self):
        context = GenerationContext(
            purpose=GenerationPurpose.FIRST_LIST,
            access_tier=GenerationAccessTier.FREE,
            environment=GenerationEnvironment.PRODUCTION,
        )

        self.assertEqual(context.access_tier, GenerationAccessTier.FREE)
        self.assertFalse(hasattr(context, "allow_local_fallback"))
        self.assertFalse(hasattr(context, "provider_failure_policy"))
        self.assertFalse(hasattr(context, "provider_order"))
        self.assertFalse(hasattr(context, "retry_policy"))


if __name__ == "__main__":
    unittest.main()
