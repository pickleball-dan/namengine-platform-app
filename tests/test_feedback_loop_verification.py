import os
import tempfile
import unittest
from unittest.mock import patch

from namengine.core.ai_generation import build_local_taste_strategy
from namengine.core.briefs import build_brief
from namengine.core.reactions import build_reaction
from namengine.core.refinement import refine_session
from namengine.core.schemas import NameResult
from namengine.core.storage import (
    get_session_snapshot,
    initialize_database,
    save_reaction,
    save_session,
)
from namengine.core.taste import build_taste_profile
from namengine.verticals import get_vertical


class FeedbackLoopVerificationTest(unittest.TestCase):
    """Proves that user input changes reach the next generation request."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "feedback-loop.sqlite3")
        self.env_patch = patch.dict(os.environ, {"NAMENGINE_DB_PATH": self.db_path})
        self.env_patch.start()
        initialize_database()

        self.vertical = get_vertical("baby")
        self.parent_brief = build_brief(
            self.vertical,
            {
                "gender": "Girl",
                "style": "Classic",
                "sound": "Soft",
                "discovery_style": "Unexpected finds",
                "familiarity_preference": "Recognizable but not overused",
                "taste_strength_name_style": 40,
                "taste_strength_fit_and_feeling": 30,
                "taste_strength_about_your_baby": 30,
            },
        )
        self.parent_results = [
            self._result("r1", "Eleanor", ["classic", "elegant"], {"classic": 0.94}),
            self._result("r2", "Maren", ["modern", "gentle"], {"modern": 0.82}),
            self._result("r3", "Nova", ["bold", "inventive"], {"bold": 0.91}),
            self._result("r4", "Clara", ["classic", "gentle"], {"gentle": 0.88}),
            self._result("r5", "Vivienne", ["elegant"], {"elegant": 0.93}),
            self._result("r6", "Juniper", ["playful", "nature"], {"playful": 0.86}),
            self._result("r7", "Maeve", ["strong", "distinctive"], {"strong": 0.87}),
            self._result("r8", "Luna", ["familiar", "soft"], {"familiar": 0.89}),
        ]
        save_session("baby-feedback-loop", "baby", self.parent_brief, self.parent_results)

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def _result(result_id, name, tags, scores):
        return NameResult(
            id=result_id,
            name=name,
            slug=name.lower(),
            tags=tags,
            scores=scores,
        )

    def _react(self, result_id, value):
        save_reaction(build_reaction("baby-feedback-loop", result_id, value))

    def test_reactions_change_the_persisted_taste_profile(self):
        self._react("r1", "love")
        self._react("r2", "maybe")
        self._react("r3", "no")

        profile = build_taste_profile("baby-feedback-loop")

        self.assertEqual(["Eleanor"], profile.loved_names)
        self.assertEqual(["Maren"], profile.maybe_names)
        self.assertEqual(["Nova"], profile.rejected_names)
        self.assertIn("classic", profile.style_preferences)
        self.assertIn("bold", profile.rejected_lanes)
        self.assertIn("Eleanor", profile.summary)
        self.assertIn("Nova", profile.summary)

    def test_refinement_forwards_feedback_instruction_and_history_to_generation(self):
        self._react("r1", "love")
        self._react("r2", "maybe")
        self._react("r3", "no")
        next_results = [self._result("n1", "Lenora", ["classic"], {"classic": 0.9})]

        with patch("namengine.core.refinement.generate_names", return_value=next_results) as generate:
            child_id, child_brief, returned_results = refine_session(
                "baby-feedback-loop",
                self.vertical,
                instruction="More elegant and less trendy.",
                use_ai=True,
            )

        self.assertEqual(next_results, returned_results)
        self.assertEqual(["Eleanor"], child_brief.liked_examples)
        self.assertEqual(["Nova"], child_brief.rejected_examples)
        self.assertEqual("More elegant and less trendy.", child_brief.notes)

        kwargs = generate.call_args.kwargs
        self.assertEqual(2, kwargs["round_number"])
        self.assertTrue(kwargs["use_ai"])
        self.assertIn("Eleanor", kwargs["taste_summary"])
        self.assertIn("Nova", kwargs["taste_summary"])
        self.assertEqual(
            [result.name for result in self.parent_results],
            kwargs["previous_names"],
        )
        self.assertEqual(["Eleanor"], kwargs["taste_profile"].loved_names)
        self.assertEqual(["Nova"], kwargs["taste_profile"].rejected_names)

        snapshot = get_session_snapshot(child_id)
        self.assertEqual("baby-feedback-loop", snapshot["session"]["parent_session_id"])
        self.assertEqual(2, snapshot["session"]["round_number"])
        self.assertEqual(
            "More elegant and less trendy.",
            snapshot["session"]["refinement_prompt"],
        )

    def test_changing_slider_emphasis_changes_generation_strategy(self):
        style_heavy = build_brief(
            self.vertical,
            {
                "style": "Classic",
                "sound": "Soft",
                "taste_strength_name_style": 80,
                "taste_strength_fit_and_feeling": 10,
                "taste_strength_about_your_baby": 10,
            },
        )
        feeling_heavy = build_brief(
            self.vertical,
            {
                "style": "Classic",
                "sound": "Soft",
                "taste_strength_name_style": 10,
                "taste_strength_fit_and_feeling": 80,
                "taste_strength_about_your_baby": 10,
            },
        )

        first = build_local_taste_strategy(self.vertical, style_heavy, 1, count=8)
        second = build_local_taste_strategy(self.vertical, feeling_heavy, 1, count=8)

        self.assertNotEqual(first["slider_weighting"], second["slider_weighting"])
        self.assertTrue(first["slider_weighting"]["has_slider_weights"])
        self.assertEqual(80, first["slider_weighting"]["weights_0_to_100"]["name style"])
        self.assertEqual(80, second["slider_weighting"]["weights_0_to_100"]["fit and feeling"])

    def test_editing_intake_changes_taste_thesis_and_prompt_direction(self):
        classic_soft = build_brief(
            self.vertical,
            {"style": "Classic", "sound": "Soft", "cultural_heritage": "Italian"},
        )
        bold_modern = build_brief(
            self.vertical,
            {"style": "Modern", "sound": "Strong", "cultural_heritage": "Italian"},
        )

        first = build_local_taste_strategy(self.vertical, classic_soft, 1, count=8)
        second = build_local_taste_strategy(self.vertical, bold_modern, 1, count=8)

        self.assertNotEqual(first["taste_thesis"], second["taste_thesis"])
        self.assertEqual("Classic", first["style_direction"])
        self.assertEqual("Soft", first["sound_direction"])
        self.assertEqual("Modern", second["style_direction"])
        self.assertEqual("Strong", second["sound_direction"])

    def test_rejected_and_previous_names_are_explicitly_blocked_next_round(self):
        self._react("r3", "no")
        profile = build_taste_profile("baby-feedback-loop")
        strategy = build_local_taste_strategy(
            self.vertical,
            self.parent_brief,
            2,
            taste_profile=profile,
            previous_names=[result.name for result in self.parent_results],
            count=8,
        )

        self.assertIn("Nova", strategy["prior_taste_summary"])
        self.assertIn("Nova", strategy["previous_names"])
        self.assertTrue(
            any("previous names" in rule.lower() for rule in strategy["avoidance_rules"])
        )


if __name__ == "__main__":
    unittest.main()
