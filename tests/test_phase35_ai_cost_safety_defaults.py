import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as platform_app
from app import create_app
from namengine.core.briefs import build_brief
from namengine.core.schemas import NameResult, ValidationResult, ValidationStatus
from namengine.verticals import get_vertical


class PhaseThirtyFiveAiCostSafetyDefaultsTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_ai_verticals = os.environ.get("NAMENGINE_AI_PRIMARY_VERTICALS")
        os.environ["NAMENGINE_DB_PATH"] = str(Path(self.tempdir.name) / "namengine.sqlite3")
        os.environ.pop("NAMENGINE_AI_PRIMARY_VERTICALS", None)
        self.client = create_app().test_client()

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

    def test_baby_pet_and_business_default_to_ai_primary_when_openai_is_configured(self):
        baby = get_vertical("baby")
        pet = get_vertical("pet")
        business = get_vertical("business")
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True):
            self.assertTrue(platform_app._should_use_ai_for_vertical(baby))
            self.assertTrue(platform_app._should_use_ai_for_vertical(pet))
            self.assertTrue(platform_app._should_use_ai_for_vertical(business))

    def test_ai_primary_default_set_comes_from_route_policy_when_env_is_absent(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(platform_app._ai_primary_verticals(), {"baby", "pet", "business"})
            self.assertNotIn("boat", platform_app._ai_primary_verticals())

    def test_ai_primary_env_override_can_narrow_vertical_opt_in(self):
        baby = get_vertical("baby")
        pet = get_vertical("pet")
        business = get_vertical("business")
        boat = get_vertical("boat")
        os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = "baby"
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True):
            self.assertTrue(platform_app._should_use_ai_for_vertical(baby))
            self.assertFalse(platform_app._should_use_ai_for_vertical(pet))
            self.assertFalse(platform_app._should_use_ai_for_vertical(business))
            self.assertFalse(platform_app._should_use_ai_for_vertical(boat))

    def test_ai_primary_env_override_special_values_are_unchanged(self):
        for value in ("", "none", "off", "false", "0"):
            with self.subTest(value=value):
                os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = value
                self.assertEqual(platform_app._ai_primary_verticals(), set())

        for value in ("all", "*"):
            with self.subTest(value=value):
                os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = value
                self.assertEqual(platform_app._ai_primary_verticals(), set(platform_app.VERTICALS))

    def test_ai_primary_env_override_keeps_existing_token_parsing(self):
        os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = " baby, boat ,unknown,, "

        self.assertEqual(platform_app._ai_primary_verticals(), {"baby", "boat", "unknown"})

    def test_pet_business_and_boat_valid_cached_ai_results_remain_reusable(self):
        cases = (
            ("pet", {"pet_type": "Dog", "vibe": "Playful"}),
            ("business", {"business_description": "Operations support", "style": "Clear"}),
            ("boat", {"vessel_type": "Sloop", "vibe": "Classic"}),
        )
        for vertical_slug, inputs in cases:
            with self.subTest(vertical=vertical_slug):
                vertical = get_vertical(vertical_slug)
                brief = build_brief(vertical, inputs)
                result = NameResult(
                    id=f"{vertical_slug}-1",
                    name="Northmark",
                    slug="northmark",
                    validation=self._validation_for_cached_result(vertical_slug),
                    metadata=self._metadata_for_cached_result(vertical_slug),
                )

                with patch.dict(
                    "os.environ",
                    {
                        "NAMENGINE_AI_PRIMARY_VERTICALS": "baby,pet,business,boat",
                        "NAMENGINE_ENVIRONMENT": "production",
                    },
                ):
                    self.assertTrue(platform_app._cached_names_match_current_rules(vertical, brief, [result]))

    def test_pet_business_and_boat_stale_fallback_handling_is_unchanged(self):
        cases = (
            ("pet", {"pet_type": "Dog", "vibe": "Playful"}),
            ("business", {"business_description": "Operations support", "style": "Clear"}),
            ("boat", {"vessel_type": "Sloop", "vibe": "Classic"}),
        )
        for vertical_slug, inputs in cases:
            with self.subTest(vertical=vertical_slug):
                vertical = get_vertical(vertical_slug)
                brief = build_brief(vertical, inputs)
                result = NameResult(
                    id=f"{vertical_slug}-1",
                    name="Northmark",
                    slug="northmark",
                    validation=self._validation_for_cached_result(vertical_slug),
                    metadata={
                        "source": f"{vertical_slug}_fallback",
                        "provider": "fallback",
                        "ai_primary_requested": True,
                        "ai_primary_fallback": True,
                    },
                )

                with patch.dict(
                    "os.environ",
                    {
                        "NAMENGINE_AI_PRIMARY_VERTICALS": "baby,pet,business,boat",
                        "NAMENGINE_ENVIRONMENT": "production",
                    },
                ):
                    self.assertFalse(platform_app._cached_names_match_current_rules(vertical, brief, [result]))

    def test_business_cache_still_requires_domain_validation_and_metadata(self):
        business = get_vertical("business")
        brief = build_brief(business, {"business_description": "Operations support", "style": "Clear"})

        with patch.dict("os.environ", {"NAMENGINE_AI_PRIMARY_VERTICALS": "business"}):
            self.assertFalse(
                platform_app._cached_names_match_current_rules(
                    business,
                    brief,
                    [
                        NameResult(
                            id="business-1",
                            name="Northmark",
                            slug="northmark",
                            validation=[],
                            metadata={"source": "openai", "provider": "openai", "domain_info": {}},
                        )
                    ],
                )
            )
            self.assertFalse(
                platform_app._cached_names_match_current_rules(
                    business,
                    brief,
                    [
                        NameResult(
                            id="business-1",
                            name="Northmark",
                            slug="northmark",
                            validation=self._validation_for_cached_result("business"),
                            metadata={"source": "openai", "provider": "openai"},
                        )
                    ],
                )
            )

    def test_business_results_route_uses_openai_prompt_pipeline_when_configured(self):
        ai_names = [
            NameResult(
                id="business-1",
                name="Northmark",
                slug="northmark",
                tagline="A confident name for operators.",
                why_this_name="Generated by the OpenAI naming prompt pipeline.",
                fit_note="Fits a credible B2B operations brief.",
                scores={"clarity": 0.9, "distinctiveness": 0.85, "market_fit": 0.88},
                metadata={"source": "openai", "provider": "openai"},
            )
        ]
        route = "/business/results?business_description=Operations+support&audience=B2B+buyers&style=Clear+and+credible"
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            platform_app, "generate_with_router", return_value=ai_names
        ) as generate:
            response = self.client.get(route)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate.call_args.kwargs["providers"], [platform_app.ModelProvider.OPENAI])
        self.assertFalse(generate.call_args.kwargs["fallback_on_provider_error"])
        self.assertIn("Northmark", response.get_data(as_text=True))
        self.assertIsInstance(ai_names[0].metadata.get("domain_info"), dict)

    def test_business_ai_results_are_domain_enriched_before_cache_validation(self):
        ai_names = [
            NameResult(
                id="business-1",
                name="Northmark",
                slug="northmark",
                tagline="A confident name for operators.",
                why_this_name="Generated by the OpenAI naming prompt pipeline.",
                fit_note="Fits a credible B2B operations brief.",
                scores={"clarity": 0.9, "distinctiveness": 0.85, "market_fit": 0.88},
                validation=[
                    ValidationResult(
                        module="business_domain",
                        status=ValidationStatus.PASS,
                        label="Domain review",
                        message="Domain quick-check attached.",
                    )
                ],
                metadata={"source": "openai", "provider": "openai"},
            )
        ]
        data = {
            "business_description": "Operations support",
            "audience": "B2B buyers",
            "style": "Clear and credible",
        }
        with patch.object(platform_app, "is_ai_generation_configured", return_value=True), patch.object(
            platform_app, "generate_with_router", return_value=ai_names
        ) as generate:
            response = self.client.post("/business/results", data=data, follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            cached = self.client.get(response.headers["Location"])

        self.assertEqual(cached.status_code, 200)
        self.assertEqual(generate.call_count, 1)
        self.assertIn("Northmark", cached.get_data(as_text=True))

    def _validation_for_cached_result(self, vertical_slug: str):
        if vertical_slug != "business":
            return []
        return [
            ValidationResult(
                module="business_domain",
                status=ValidationStatus.PASS,
                label="Domain review",
                message="Domain quick-check attached.",
            )
        ]

    def _metadata_for_cached_result(self, vertical_slug: str):
        metadata = {"source": "openai", "provider": "openai"}
        if vertical_slug == "business":
            metadata["domain_info"] = {"primary": "northmark.com", "display_status": {"status": "available"}}
        return metadata


if __name__ == "__main__":
    unittest.main()
