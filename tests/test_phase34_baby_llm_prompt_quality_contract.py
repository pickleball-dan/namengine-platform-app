import unittest

from app import create_app
from namengine.core.ai_generation import build_generation_prompt
from namengine.core.briefs import build_brief
from namengine.verticals import get_vertical


class PhaseThirtyFourBabyLlmPromptQualityContractTest(unittest.TestCase):
    def setUp(self):
        create_app()
        self.vertical = get_vertical("baby")

    def test_baby_cultural_heritage_prompt_makes_llm_the_creative_source(self):
        brief = build_brief(
            self.vertical,
            {
                "gender": "Girl",
                "style": "Playful",
                "cultural_heritage": "Japanese",
            },
        )
        prompt = build_generation_prompt(
            vertical=self.vertical,
            brief=brief,
            round_number=1,
            taste_profile=None,
            previous_names=[],
            count=8,
            taste_strategy={"taste_thesis": "Playful Japanese girl names."},
        )

        self.assertTrue(prompt["generation_rules"]["llm_is_creative_source_not_local_pool"])
        self.assertTrue(prompt["generation_rules"]["do_not_limit_candidates_to_any_preexisting_app_list"])
        guidance = prompt["baby_generation_guidance"]
        self.assertEqual(guidance["cultural_heritage_is_primary_creative_source"], "Japanese")
        self.assertTrue(guidance["generate_authentic_culturally_grounded_options"])
        self.assertTrue(guidance["meaning_and_vibe_are_first_class"])
        self.assertTrue(guidance["final_list_should_show_breadth_within_the_heritage_not_breadth_away_from_it"])


if __name__ == "__main__":
    unittest.main()
