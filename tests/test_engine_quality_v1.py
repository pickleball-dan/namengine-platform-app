import json
import os
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch

from app import create_app
from namengine.core import (
    BABY_PROMPT_VERSION,
    QualityAdapter,
    build_brief,
    generate_ai_names,
    load_taste_engine_fixtures,
    run_taste_engine_fixture_set,
    save_session,
    score_name_result,
    select_best_candidates,
)
from namengine.core.ai_generation import build_local_taste_strategy
from namengine.core.baby_quality_adapter import (
    BABY_QUALITY_SCORE_WEIGHTS,
    improve_baby_explanations,
)
from namengine.core.prompt_versions import DEFAULT_PROMPT_VERSION, prompt_version_for
from namengine.core.quality_framework import (
    build_quality_taste_thesis,
    evaluate_quality_attributes,
    quality_adapter_for,
    rank_quality_candidates,
    register_quality_adapter,
    score_quality_result,
    unregister_quality_adapter,
)
from namengine.core.schemas import GenerationCandidate, ModelProvider, NameResult, NamingBrief
from namengine.verticals import get_vertical


AI_RESPONSE = json.dumps(
    {
        "names": [
            {
                "name": "Aiko",
                "pronunciation": "EYE-koh",
                "tagline": "Bright, playful, and compact.",
                "origin": "Japanese",
                "meaning": "Often associated with beloved child, depending on kanji.",
                "why_this_name": "Aiko has a lovely meaning.",
                "fit_note": "A good name.",
                "risks": ["Confirm the preferred kanji and meaning with family."],
                "tags": ["Japanese", "playful", "bright"],
                "scores": {
                    "fit": 0.9,
                    "usability": 0.86,
                    "distinctiveness": 0.78,
                    "cultural_alignment": 0.95,
                    "sound": 0.9,
                    "explanation_quality": 0.72,
                },
            }
        ]
    }
)


class FakeResponse:
    output_text = AI_RESPONSE
    usage = {"input_tokens": 100, "output_tokens": 60, "total_tokens": 160}


class FakeResponses:
    def create(self, **kwargs):
        return FakeResponse()


class FakeClient:
    responses = FakeResponses()


class EngineQualityV1Test(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_engine_audit_enabled = os.environ.get("NAMENGINE_ENABLE_ENGINE_AUDIT")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "quality.sqlite3")
        os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = "1"
        self.vertical = get_vertical("baby")
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_engine_audit_enabled is None:
            os.environ.pop("NAMENGINE_ENABLE_ENGINE_AUDIT", None)
        else:
            os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = self.previous_engine_audit_enabled
        self.tempdir.cleanup()

    def _quality_brief(self):
        brief = build_brief(
            self.vertical,
            {
                "gender": "Girl",
                "style": "Modern",
                "familiarity_preference": "A little less common",
                "timeless_vs_distinctive": "Mostly distinctive",
                "sound": "Playful",
                "cultural_heritage": "Japanese",
                "cultural_context": "Family heritage",
                "family_context": "Readable in Japan and the US",
                "discovery_style": "Balanced mix",
                "avoid": "Sakura",
                "notes": "Bright without becoming cutesy.",
            },
        )
        brief.inputs["taste_strength_about_your_baby"] = 25
        brief.inputs["taste_strength_name_style"] = 45
        brief.inputs["taste_strength_fit_and_feeling"] = 30
        return brief

    def test_baby_prompt_version_is_persisted_and_visible_in_engine_audit(self):
        brief = self._quality_brief()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            results = generate_ai_names(
                self.vertical,
                brief,
                round_number=1,
                client_factory=FakeClient,
            )

        self.assertEqual(results[0].metadata["prompt_version"], BABY_PROMPT_VERSION)
        self.assertEqual(
            results[0].metadata["ai_calls"][0]["prompt_version"],
            BABY_PROMPT_VERSION,
        )
        save_session("baby-quality-prompt", "baby", brief, results)
        response = self.client.get("/dev/engine-audit/baby-quality-prompt")
        self.assertEqual(response.status_code, 200)
        self.assertIn(BABY_PROMPT_VERSION, response.get_data(as_text=True))

    def test_taste_thesis_covers_every_baby_quality_signal(self):
        strategy = build_local_taste_strategy(self.vertical, self._quality_brief(), 1)
        thesis = strategy["taste_thesis"]

        for expected in (
            "Style: Modern",
            "Familiarity: A little less common",
            "Distinctiveness: Mostly distinctive",
            "Sound: Playful",
            "Japanese",
            "Readable in Japan and the US",
            "Discovery: Balanced mix",
            "name style 45/100",
            "Sakura",
            "Bright without becoming cutesy",
        ):
            self.assertIn(expected, thesis)

    def test_baby_score_has_documented_dimensions_and_local_overall(self):
        brief = self._quality_brief()
        result = NameResult(
            id="baby-aiko",
            name="Aiko",
            slug="aiko",
            pronunciation="EYE-koh",
            tagline="Japanese-rooted, bright, and playful.",
            origin="Japanese",
            meaning="Beloved child, depending on kanji.",
            why_this_name="Aiko fits the modern playful Japanese family brief.",
            fit_note="Best for a bright, less common direction.",
            risks=["Confirm kanji and meaning with family."],
            tags=["Japanese", "modern", "playful"],
            scores={"distinctiveness": 0.78, "callability": 0.9},
        )

        score, reasons = score_name_result(
            result,
            ModelProvider.OPENAI,
            brief=brief,
            vertical=self.vertical,
        )

        structured = result.metadata["quality_scores"]
        self.assertEqual(
            set(structured),
            set(BABY_QUALITY_SCORE_WEIGHTS) | {"overall"},
        )
        expected = round(
            sum(structured[key] * weight for key, weight in BABY_QUALITY_SCORE_WEIGHTS.items()),
            3,
        )
        self.assertEqual(score, expected)
        self.assertEqual(structured["overall"], expected)
        self.assertTrue(reasons)

    def test_baby_ranking_uses_deterministic_name_tie_breaker(self):
        zora = GenerationCandidate(
            result=NameResult(id="baby-2", name="Zora", slug="zora"),
            provider=ModelProvider.OPENAI,
            quality_score=0.8,
        )
        aiko = GenerationCandidate(
            result=NameResult(id="baby-1", name="Aiko", slug="aiko"),
            provider=ModelProvider.OPENAI,
            quality_score=0.8,
        )

        forward = select_best_candidates([zora, aiko], 2, vertical_slug="baby")
        reverse = select_best_candidates([aiko, zora], 2, vertical_slug="baby")

        self.assertEqual([item.result.name for item in forward], ["Aiko", "Zora"])
        self.assertEqual([item.result.name for item in reverse], ["Aiko", "Zora"])

    def test_explanations_are_specific_concise_honest_and_varied(self):
        results = [
            NameResult(
                id=f"baby-{index}",
                name=name,
                slug=name.lower(),
                origin="Japanese",
                why_this_name="A lovely name with a lovely meaning.",
                fit_note="A good fit.",
                risks=["Confirm the preferred kanji with family."],
            )
            for index, name in enumerate(("Aiko", "Kiko", "Yumi"), start=1)
        ]

        improve_baby_explanations(results, self._quality_brief())

        for result in results:
            self.assertIn("modern", result.why_this_name.lower())
            self.assertIn("playful", result.why_this_name.lower())
            self.assertIn("tradeoff:", result.why_this_name.lower())
            self.assertLessEqual(len(result.why_this_name.split()), 68)
            self.assertNotIn("lovely meaning", result.why_this_name.lower())
        openings = {" ".join(result.why_this_name.split()[:4]) for result in results}
        self.assertEqual(len(openings), 3)

    def test_requested_fixtures_use_attribute_thresholds_not_exact_names(self):
        requested_ids = {
            "baby-classic-soft-familiar",
            "baby-rare-strong-distinctive",
            "baby-japanese-heritage-playful",
            "baby-african-american-historical",
            "baby-scandinavian-minimalist",
            "baby-culturally-neutral-unexpected",
        }
        fixtures = [
            fixture for fixture in load_taste_engine_fixtures() if fixture.id in requested_ids
        ]
        self.assertEqual({fixture.id for fixture in fixtures}, requested_ids)
        self.assertTrue(all(fixture.quality_thresholds for fixture in fixtures))

        evaluations = run_taste_engine_fixture_set(fixtures, use_ai=False)

        expected_attributes = {
            "style_alignment",
            "familiarity_alignment",
            "distinctiveness_alignment",
            "sound_alignment",
            "cultural_context_alignment",
            "explanation_specificity",
            "list_diversity",
            "absence_of_obvious_brief_violations",
        }
        for evaluation in evaluations:
            self.assertEqual(set(evaluation.attribute_scores), expected_attributes)
            self.assertTrue(evaluation.quality_passed, (evaluation.fixture.id, evaluation.attribute_scores))

    def test_baby_is_a_registered_platform_adapter(self):
        adapter = quality_adapter_for("baby")

        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.prompt_version, BABY_PROMPT_VERSION)
        self.assertEqual(prompt_version_for("baby"), BABY_PROMPT_VERSION)
        self.assertEqual(adapter.score_weights, BABY_QUALITY_SCORE_WEIGHTS)

    def test_shared_framework_supports_a_minimal_non_baby_adapter(self):
        slug = "test-minimal"
        adapter = QualityAdapter(
            vertical_slug=slug,
            prompt_version="test-minimal-prompt-v1",
            score_version="test-minimal-score-v1",
            score_weights={"fit": 0.75, "clarity": 0.25},
            model_score_keys=("fit", "clarity"),
            prompt_guidance=("Be concrete.",),
            build_taste_thesis=lambda brief, weighting: f"Tone: {brief.inputs['tone']}",
            score_dimensions=lambda result, brief: (
                {"fit": result.scores["fit"], "clarity": result.scores["clarity"]},
                ["configured dimensions"],
            ),
            evaluate_attributes=lambda brief, results: {"list_quality": 0.9},
        )
        register_quality_adapter(adapter)
        self.addCleanup(unregister_quality_adapter, slug)
        brief = NamingBrief(vertical=slug, inputs={"tone": "Direct"})
        result = NameResult(
            id="test-one",
            name="One",
            slug="one",
            scores={"fit": 0.8, "clarity": 0.6},
        )

        score, reasons = score_quality_result(slug, result, brief)

        self.assertEqual(build_quality_taste_thesis(slug, brief, {}), "Tone: Direct")
        self.assertEqual(prompt_version_for(slug), "test-minimal-prompt-v1")
        self.assertEqual(score, 0.75)
        self.assertEqual(reasons, ["configured dimensions"])
        self.assertEqual(result.metadata["quality_score_version"], "test-minimal-score-v1")
        self.assertEqual(evaluate_quality_attributes(slug, brief, [result]), {"list_quality": 0.9})

        unregister_quality_adapter(slug)
        self.assertIsNone(quality_adapter_for(slug))
        self.assertEqual(prompt_version_for(slug), DEFAULT_PROMPT_VERSION)

    def test_adapter_registration_rejects_invalid_or_conflicting_configuration(self):
        with self.assertRaises(ValueError):
            QualityAdapter(
                vertical_slug="Invalid Slug",
                prompt_version="prompt-v1",
                score_version="score-v1",
                score_weights={"fit": 1.0},
                model_score_keys=("fit",),
                prompt_guidance=(),
                build_taste_thesis=lambda brief, weighting: "test",
                score_dimensions=lambda result, brief: ({"fit": 1.0}, []),
            )
        with self.assertRaises(ValueError):
            QualityAdapter(
                vertical_slug="invalid-weights",
                prompt_version="prompt-v1",
                score_version="score-v1",
                score_weights={"fit": 1.1, "clarity": -0.1},
                model_score_keys=("fit", "clarity"),
                prompt_guidance=(),
                build_taste_thesis=lambda brief, weighting: "test",
                score_dimensions=lambda result, brief: ({"fit": 1.0, "clarity": 0.0}, []),
            )
        valid = QualityAdapter(
            vertical_slug="test-conflict",
            prompt_version="prompt-v1",
            score_version="score-v1",
            score_weights={"fit": 1.0},
            model_score_keys=("fit",),
            prompt_guidance=(),
            build_taste_thesis=lambda brief, weighting: "test",
            score_dimensions=lambda result, brief: ({"fit": 1.0}, []),
        )
        register_quality_adapter(valid)
        self.addCleanup(unregister_quality_adapter, valid.vertical_slug)
        with self.assertRaises(ValueError):
            register_quality_adapter(replace(valid, prompt_version="prompt-v2"))

    def test_deterministic_ranking_is_shared_and_pet_keeps_legacy_order(self):
        slug = "test-ranking"
        register_quality_adapter(
            QualityAdapter(
                vertical_slug=slug,
                prompt_version="test-ranking-prompt-v1",
                score_version="test-ranking-score-v1",
                score_weights={"fit": 1.0},
                model_score_keys=("fit",),
                prompt_guidance=(),
                build_taste_thesis=lambda brief, weighting: "test",
                score_dimensions=lambda result, brief: ({"fit": 0.8}, []),
            )
        )
        self.addCleanup(unregister_quality_adapter, slug)
        zora = GenerationCandidate(
            result=NameResult(id="2", name="Zora", slug="zora"),
            provider=ModelProvider.FALLBACK,
            quality_score=0.8,
        )
        aiko = GenerationCandidate(
            result=NameResult(id="1", name="Aiko", slug="aiko"),
            provider=ModelProvider.FALLBACK,
            quality_score=0.8,
        )

        self.assertEqual(
            [item.result.name for item in rank_quality_candidates([zora, aiko], slug)],
            ["Aiko", "Zora"],
        )
        self.assertIsNone(quality_adapter_for("pet"))
        self.assertEqual(
            [item.result.name for item in rank_quality_candidates([zora, aiko], "pet")],
            ["Zora", "Aiko"],
        )

        first_variant = GenerationCandidate(
            result=NameResult(id="z-id", name="Aiko", slug="aiko", origin="Zulu"),
            provider=ModelProvider.FALLBACK,
            quality_score=0.8,
        )
        second_variant = GenerationCandidate(
            result=NameResult(id="a-id", name="Aiko", slug="aiko", origin="Japanese"),
            provider=ModelProvider.FALLBACK,
            quality_score=0.8,
        )
        ranked_variants = rank_quality_candidates([first_variant, second_variant], slug)
        self.assertEqual([item.result.origin for item in ranked_variants], ["Japanese", "Zulu"])


if __name__ == "__main__":
    unittest.main()
