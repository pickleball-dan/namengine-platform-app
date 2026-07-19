import unittest

from app import create_app
from namengine.core.ai_generation import build_finalizer_prompt, build_generation_prompt, build_taste_interpreter_prompt
from namengine.core.briefs import build_brief
from namengine.verticals import get_vertical


class PhaseThirtySixLlmCycleWeightingContractTest(unittest.TestCase):
    def setUp(self):
        create_app()
        self.vertical = get_vertical("baby")
        self.brief = build_brief(
            self.vertical,
            {
                "gender": "Girl",
                "style": "Playful",
                "cultural_heritage": "Japanese",
            },
        )
        self.brief.inputs["taste_strength_about_your_baby"] = 35
        self.brief.inputs["taste_strength_name_style"] = 95
        self.brief.inputs["taste_strength_fit_and_feeling"] = 80

    def test_taste_interpreter_prompt_receives_slider_weighting(self):
        prompt = build_taste_interpreter_prompt(
            vertical=self.vertical,
            brief=self.brief,
            round_number=1,
            taste_profile=None,
            previous_names=[],
            count=8,
        )

        weighting = prompt["taste_weighting"]
        self.assertTrue(weighting["has_slider_weights"])
        self.assertEqual(weighting["strongest_signal"], "name style")
        self.assertEqual(weighting["weights_0_to_100"]["name style"], 95)
        self.assertTrue(prompt["interpretation_rules"]["use_slider_weights_to_prioritize_prompt_tradeoffs"])

    def test_candidate_generation_prompt_uses_slider_weighting_for_pool(self):
        prompt = build_generation_prompt(
            vertical=self.vertical,
            brief=self.brief,
            round_number=1,
            taste_profile=None,
            previous_names=[],
            count=8,
            taste_strategy={"taste_thesis": "Playful Japanese girl names."},
        )

        self.assertEqual(prompt["count"], 8)
        self.assertEqual(prompt["output_contract"]["top_level_keys"], ["candidate_pool"])
        self.assertTrue(prompt["generation_rules"]["weight_final_selection_according_to_slider_priorities"])
        self.assertEqual(prompt["taste_weighting"]["strongest_signal"], "name style")

    def test_finalizer_prompt_uses_slider_weighting_and_candidate_pool(self):
        prompt = build_finalizer_prompt(
            vertical=self.vertical,
            brief=self.brief,
            round_number=1,
            taste_profile=None,
            previous_names=[],
            count=8,
            taste_strategy={"taste_thesis": "Playful Japanese girl names."},
            candidate_pool=[{"name": "Aiko", "territory": "playful Japanese", "rationale": "Bright and warm."}],
        )

        self.assertEqual(prompt["output_contract"]["top_level_keys"], ["names", "rejected_candidates"])
        self.assertEqual(prompt["taste_weighting"]["strongest_signal"], "name style")
        self.assertEqual(prompt["candidate_pool"][0]["name"], "Aiko")
        self.assertTrue(prompt["finalizer_rules"]["only_choose_from_candidate_pool"])


if __name__ == "__main__":
    unittest.main()
