import os
import tempfile
import unittest

from app import create_app
from namengine.core import build_brief, save_session, score_name_result
from namengine.core.prompt_versions import DEFAULT_PROMPT_VERSION, prompt_version_for
from namengine.core.model_router import score_provider_results
from namengine.core.quality_framework import (
    apply_quality_metadata,
    quality_adapter_for,
    quality_model_score_keys,
    quality_prompt_guidance,
    score_quality_result,
)
from namengine.core.schemas import ModelProvider, NameResult, ProviderResult, ValidationStatus
from namengine.core.validation import validate_result, validate_results
from namengine.verticals import BABY, BOAT, BUSINESS, PET


class BoatValidationQualityParityTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "test.sqlite3")
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        self.tempdir.cleanup()

    def test_boat_validation_uses_declared_modules(self):
        brief = _boat_brief(avoid="Sea Witch")
        result = NameResult(id="boat-1", name="Sea Witch", slug="sea-witch")

        validation = validate_result(BOAT, brief, result)

        modules = {item.module for item in validation}
        self.assertIn("boat_radio_clarity", modules)
        self.assertIn("boat_tradition_fit", modules)
        self.assertIn("boat_length", modules)
        self.assertIn("avoid_match", modules)
        self.assertNotIn("validation_not_configured", modules)
        avoid = next(item for item in validation if item.module == "avoid_match")
        self.assertEqual(avoid.status, ValidationStatus.FAIL)

    def test_boat_quality_adapter_is_registered_and_scores_metadata(self):
        adapter = quality_adapter_for("boat")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.vertical_slug, "boat")

        brief = _boat_brief()
        result = _boat_result("Harbor Star")

        score, reasons = score_quality_result("boat", result, brief)

        self.assertGreater(score, 0.7)
        self.assertTrue(reasons)
        self.assertEqual(result.metadata["quality_score_version"], "boat-quality-score-v1")
        self.assertIn("radio_clarity", result.metadata["quality_scores"])
        self.assertIn("vessel_fit", result.metadata["quality_scores"])
        self.assertIn("nautical_character", result.metadata["quality_scores"])
        self.assertIn("overall", result.metadata["quality_scores"])

    def test_boat_adapter_preserves_legacy_generation_prompt_fields(self):
        legacy_score_keys = ("callability", "warmth", "distinctiveness")

        self.assertEqual(prompt_version_for("boat"), DEFAULT_PROMPT_VERSION)
        self.assertEqual(quality_model_score_keys("boat", legacy_score_keys), legacy_score_keys)
        self.assertEqual(quality_prompt_guidance("boat", ()), ())

    def test_boat_router_scoring_uses_adapter_instead_of_generic_fallback(self):
        brief = _boat_brief()
        result = _boat_result("Harbor Star")

        score, reasons = score_name_result(result, ModelProvider.OPENAI, brief=brief, vertical=BOAT)

        self.assertGreater(score, 0.7)
        self.assertEqual(result.metadata["quality_score_version"], "boat-quality-score-v1")
        self.assertIn("quality_scores", result.metadata)
        self.assertNotIn("openai candidate", reasons)

        provider_results = [ProviderResult(provider=ModelProvider.OPENAI, names=[result])]
        candidates = score_provider_results(provider_results, brief=brief, vertical=BOAT)
        self.assertEqual(candidates[0].result.metadata["quality_score_version"], "boat-quality-score-v1")

    def test_boat_validation_quality_results_render_normally(self):
        brief = _boat_brief()
        results = validate_results(BOAT, brief, [_boat_result("Harbor Star")])
        apply_quality_metadata("boat", results, brief)
        save_session("boat-quality-session", "boat", brief, results)

        response = self.client.get("/results/session/boat-quality-session")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Harbor Star", body)
        self.assertIn("Validation", body)
        self.assertIn("Radio clarity", body)
        self.assertNotIn("validation_not_configured", body)

    def test_other_active_vertical_adapters_still_register(self):
        self.assertIsNotNone(quality_adapter_for(BABY.slug))
        self.assertIsNotNone(quality_adapter_for(PET.slug))
        self.assertIsNotNone(quality_adapter_for(BUSINESS.slug))


def _boat_brief(avoid: str = ""):
    return build_brief(
        BOAT,
        {
            "boat_type": "Sailboat",
            "boat_size": "30-45ft",
            "use": "Weekend adventures",
            "waters": "Coastal / ocean",
            "crew": "Family and friends",
            "name_type": "Classic nautical",
            "vibe": "Adventurous and elegant",
            "radio_name": "Very important",
            "inspiration": "Harbors, stars, and family trips",
            "avoid": avoid,
        },
    )


def _boat_result(name: str) -> NameResult:
    slug = name.lower().replace(" ", "-")
    return NameResult(
        id=f"boat-{slug}",
        name=name,
        slug=slug,
        pronunciation="HAR-bor star",
        tagline="Classic, clear, and coastal.",
        meaning="A name that suggests safe harbor, night passages, and a bright point to follow.",
        why_this_name="Harbor Star fits a family sailboat with coastal use, clear radio sound, and classic nautical character.",
        fit_note="Best for a boat that should feel traditional, memorable, and easy to say at the dock.",
        risks=["Confirm no similar vessel name in the marina."],
        tags=["nautical", "classic", "coastal", "family"],
        scores={
            "radio_clarity": 0.91,
            "vessel_fit": 0.88,
            "nautical_character": 0.9,
            "memorability": 0.86,
            "distinctiveness": 0.72,
        },
    )


if __name__ == "__main__":
    unittest.main()
