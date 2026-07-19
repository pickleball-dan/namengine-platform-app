import unittest

from namengine.core.ai_generation import (
    _call_audit_summary,
    build_generation_prompt,
    build_local_taste_strategy,
    build_taste_interpreter_prompt,
)
from namengine.core.briefs import build_brief
from namengine.verticals import BABY, PET
from namengine.verticals.baby_taxonomy import BABY_TAXONOMY, BABY_TAXONOMY_VERSION


PROMPT_AXES = {
    "style": "style_direction",
    "sound": "sound_direction",
    "familiarity_preference": "familiarity_direction",
    "timeless_vs_distinctive": "distinctiveness_direction",
    "discovery_style": "discovery_direction",
    "cultural_context": "inspiration_direction",
}


class BabyTaxonomyAiGenerationV1Test(unittest.TestCase):
    def _baby_brief(self, **overrides):
        inputs = {"gender": "Girl", "style": "Classic", "sound": "Soft"}
        inputs.update(overrides)
        return build_brief(BABY, inputs)

    def _generation_prompt(self, brief):
        strategy = build_local_taste_strategy(BABY, brief, round_number=1)
        return build_generation_prompt(
            vertical=BABY,
            brief=brief,
            round_number=1,
            taste_profile=None,
            previous_names=[],
            count=8,
            taste_strategy=strategy,
        )

    def test_every_canonical_taste_option_reaches_all_ai_prompt_projections(self):
        for field_id, prompt_key in PROMPT_AXES.items():
            for option in BABY_TAXONOMY.current_choices(field_id):
                with self.subTest(field_id=field_id, option=option):
                    brief = self._baby_brief(**{field_id: option})
                    strategy = build_local_taste_strategy(BABY, brief, round_number=1)
                    generation = self._generation_prompt(brief)
                    interpreter = build_taste_interpreter_prompt(
                        BABY,
                        brief,
                        round_number=1,
                        taste_profile=None,
                        previous_names=[],
                        count=8,
                    )

                    for projection in (
                        strategy["baby_taxonomy_projection"],
                        generation["baby_taxonomy_projection"],
                        interpreter["baby_taxonomy_projection"],
                    ):
                        self.assertEqual(option, projection[prompt_key])

    def test_existing_prompt_fields_use_taxonomy_projected_labels(self):
        brief = self._baby_brief(
            style="Modern",
            sound="Playful",
            familiarity_preference="Recognizable but not overused",
            timeless_vs_distinctive="Mostly distinctive",
            discovery_style="Unexpected finds",
            cultural_context="Meaning first",
        )
        strategy = build_local_taste_strategy(BABY, brief, round_number=2)
        prompt = build_generation_prompt(
            vertical=BABY,
            brief=brief,
            round_number=2,
            taste_profile=None,
            previous_names=[],
            count=8,
            taste_strategy=strategy,
        )

        self.assertEqual("Modern", strategy["style_direction"])
        self.assertEqual("Playful", strategy["sound_direction"])
        self.assertEqual("Unexpected finds", strategy["discovery_direction"])
        self.assertEqual("Recognizable but not overused", strategy["familiarity_direction"])
        self.assertEqual("Modern", prompt["baby_generation_guidance"]["style_signal"])
        self.assertEqual(
            "Meaning first",
            prompt["baby_generation_guidance"]["additional_cultural_context"],
        )

    def test_legacy_intake_labels_keep_their_existing_prompt_values(self):
        legacy = build_brief(
            BABY,
            {
                "baby_gender": "Girl",
                "name_style": "Elegant",
                "sound_preference": "Clear",
                "discovery_style": "Familiar favorites",
                "familiarity_preference": "Very familiar",
                "cultural_context": "Honor names",
            },
        )
        projection = self._generation_prompt(legacy)["baby_taxonomy_projection"]

        self.assertEqual("Elegant", projection["style_direction"])
        self.assertEqual("Clear", projection["sound_direction"])
        self.assertEqual("Familiar favorites", projection["discovery_direction"])
        self.assertEqual("Very familiar", projection["familiarity_direction"])
        self.assertEqual("Honor names", projection["inspiration_direction"])

    def test_baby_taxonomy_version_is_internal_prompt_and_call_diagnostic(self):
        prompt = self._generation_prompt(self._baby_brief())
        audit = _call_audit_summary(
            "candidate_generator_ranker_v1",
            {"model": "test-model", "latency_ms": 1, "usage": {}, "schema_name": "test"},
            prompt,
        )

        self.assertEqual(BABY_TAXONOMY_VERSION, prompt["baby_taxonomy_version"])
        self.assertEqual(BABY_TAXONOMY_VERSION, audit["baby_taxonomy_version"])

    def test_non_baby_ai_prompt_contract_has_no_taxonomy_changes(self):
        brief = build_brief(PET, {"pet_type": "Dog", "style": "Classic", "vibe": "Playful"})
        strategy = build_local_taste_strategy(PET, brief, round_number=1)
        generation = build_generation_prompt(
            vertical=PET,
            brief=brief,
            round_number=1,
            taste_profile=None,
            previous_names=[],
            count=8,
            taste_strategy=strategy,
        )
        interpreter = build_taste_interpreter_prompt(
            PET,
            brief,
            round_number=1,
            taste_profile=None,
            previous_names=[],
            count=8,
        )

        for payload in (strategy, generation, interpreter):
            self.assertNotIn("baby_taxonomy_version", payload)
            self.assertNotIn("baby_taxonomy_projection", payload)
        self.assertEqual({}, generation["baby_generation_guidance"])


if __name__ == "__main__":
    unittest.main()
