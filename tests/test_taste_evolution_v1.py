import os
import tempfile
import unittest

from app import create_app
from namengine.core import (
    build_brief,
    build_reaction,
    build_taste_profile,
    save_reaction,
    save_session,
    save_taste_profile,
)
from namengine.core.schemas import NameResult, TasteProfile
from namengine.verticals import BABY


class TasteEvolutionV1Test(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_engine_audit_enabled = os.environ.get("NAMENGINE_ENABLE_ENGINE_AUDIT")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "taste-evolution.sqlite3")
        os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = "1"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        self._seed_rounds()

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

    def _seed_rounds(self):
        parent_inputs = {
            "gender": "Girl",
            "style": "Classic",
            "sound": "Soft",
            "cultural_heritage": "Nordic",
            "familiarity_preference": "Highly familiar",
            "taste_strength_about_your_baby": 25,
            "taste_strength_name_style": 40,
            "taste_strength_fit_and_feeling": 35,
        }
        child_inputs = {
            "gender": "Girl",
            "style": "Distinctive",
            "sound": "Crisp",
            "cultural_heritage": "Nordic",
            "discovery_style": "Bolder discoveries",
            "taste_strength_about_your_baby": 15,
            "taste_strength_name_style": 65,
            "taste_strength_fit_and_feeling": 20,
        }
        parent_brief = build_brief(BABY, parent_inputs)
        child_brief = build_brief(BABY, child_inputs)
        parent_brief.inputs.update(
            {key: value for key, value in parent_inputs.items() if key.startswith("taste_strength_")}
        )
        child_brief.inputs.update(
            {key: value for key, value in child_inputs.items() if key.startswith("taste_strength_")}
        )
        child_brief.liked_examples = ["Astrid"]
        child_brief.rejected_examples = ["Olivia"]
        child_brief.notes = "More Nordic and distinctive, with crisper sounds."

        self.parent_names = self._names(
            "parent",
            [
                ("Astrid", ["shared-signal", "Nordic", "distinctive"]),
                ("Olivia", ["shared-signal", "classic", "familiar"]),
                ("Freya", ["Nordic", "soft"]),
                ("Clara", ["classic", "soft"]),
                ("Elise", ["European", "soft"]),
                ("Nora", ["Nordic", "familiar"]),
                ("Sophie", ["classic", "familiar"]),
                ("Vera", ["vintage", "crisp"]),
            ],
            "A classic, soft, familiar list with a light Nordic lane.",
            ["classic-familiar", "soft-nordic"],
        )
        self.child_names = self._names(
            "child",
            [
                ("Ingrid", ["Nordic", "distinctive"]),
                ("Sigrid", ["Nordic", "crisp"]),
                ("Dagny", ["Nordic", "rare"]),
                ("Liv", ["Nordic", "compact"]),
                ("Solveig", ["Nordic", "distinctive"]),
                ("Thora", ["Nordic", "strong"]),
                ("Eira", ["Nordic", "bright"]),
                ("Annika", ["Nordic", "crisp"]),
            ],
            "A more Nordic, distinctive list with crisp sounds and less familiarity.",
            ["nordic-distinctive", "crisp-compact"],
        )

        save_session("taste-parent", "baby", parent_brief, self.parent_names, round_number=1)
        save_reaction(build_reaction("taste-parent", self.parent_names[0].id, "love"))
        save_reaction(build_reaction("taste-parent", self.parent_names[2].id, "maybe"))
        save_reaction(build_reaction("taste-parent", self.parent_names[1].id, "no"))
        build_taste_profile("taste-parent")

        save_session(
            "taste-child",
            "baby",
            child_brief,
            self.child_names,
            round_number=2,
            parent_session_id="taste-parent",
            refinement_prompt="More Nordic and distinctive, with crisper sounds.",
        )
        save_taste_profile(
            TasteProfile(
                session_id="taste-child",
                vertical="baby",
                loved_names=["Astrid"],
                maybe_names=["Freya"],
                rejected_names=["Olivia"],
                liked_sounds=["a", "d"],
                disliked_sounds=["o", "a"],
                style_preferences={"Nordic": 1.0, "distinctive": 0.95},
                rejected_lanes=["classic", "familiar"],
                summary="Stronger Nordic and distinctive direction; avoid highly familiar choices.",
            )
        )

    @staticmethod
    def _names(prefix, values, thesis, territories):
        strategy = {
            "taste_thesis": thesis,
            "naming_territories": [{"label": label} for label in territories],
        }
        return [
            NameResult(
                id=f"{prefix}-{index:02d}",
                name=name,
                slug=name.lower(),
                tagline=f"{name} diagnostic result",
                tags=tags,
                metadata={"taste_strategy": strategy},
            )
            for index, (name, tags) in enumerate(values, start=1)
        ]

    def test_route_is_404_when_gate_is_missing_or_not_one(self):
        for value in (None, "", "0", "true", " 1"):
            with self.subTest(value=value):
                if value is None:
                    os.environ.pop("NAMENGINE_ENABLE_ENGINE_AUDIT", None)
                else:
                    os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = value
                response = self.client.get("/dev/taste-evolution/taste-child")
                self.assertEqual(response.status_code, 404)
        os.environ["NAMENGINE_ENABLE_ENGINE_AUDIT"] = "1"

    def test_route_works_when_enabled(self):
        response = self.client.get("/dev/taste-evolution/taste-child")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for section in (
            "A. Previous Round",
            "B. User Changes",
            "C. What the Engine Learned",
            "D. New Round",
            "E. Plain-English Summary",
        ):
            self.assertIn(section, body)

    def test_parent_and_child_rounds_are_compared_correctly(self):
        body = self.client.get("/dev/taste-evolution/taste-child").get_data(as_text=True)

        self.assertIn("Round 1", body)
        self.assertIn("Round 2", body)
        self.assertIn("A classic, soft, familiar list", body)
        self.assertIn("A more Nordic, distinctive list", body)
        self.assertIn("Astrid diagnostic result", body)
        self.assertIn("Ingrid diagnostic result", body)
        self.assertIn("Previous names excluded", body)
        self.assertIn("Astrid, Olivia, Freya, Clara, Elise, Nora, Sophie, Vera", body)

    def test_reactions_and_carried_names_appear_correctly(self):
        body = self.client.get("/dev/taste-evolution/taste-child").get_data(as_text=True)

        self.assertIn("Love reactions", body)
        self.assertIn("Maybe reactions", body)
        self.assertIn("No reactions", body)
        self.assertIn("Astrid", body)
        self.assertIn("Freya", body)
        self.assertIn("Olivia", body)
        self.assertIn("Astrid · carried forward", body)
        self.assertIn("Olivia · carried forward", body)

    def test_slider_and_intake_differences_are_labeled(self):
        body = self.client.get("/dev/taste-evolution/taste-child").get_data(as_text=True)

        self.assertIn("Name Style", body)
        self.assertIn("40 → 65", body)
        self.assertIn("Fit And Feeling", body)
        self.assertIn("35 → 20", body)
        self.assertIn("Increased", body)
        self.assertIn("Decreased", body)
        self.assertIn("Added", body)
        self.assertIn("Removed", body)
        self.assertIn("Unchanged", body)
        self.assertIn("Cultural Heritage", body)
        self.assertIn("More Nordic and distinctive, with crisper sounds.", body)

    def test_summary_does_not_treat_shared_tags_as_opposite_directions(self):
        body = self.client.get("/dev/taste-evolution/taste-child").get_data(as_text=True)

        self.assertNotIn("increased shared-signal", body)
        self.assertNotIn("moved away from shared-signal", body)

    def test_audit_detail_links_only_child_session_to_taste_evolution(self):
        child_body = self.client.get("/dev/engine-audit/taste-child").get_data(as_text=True)
        parent_body = self.client.get("/dev/engine-audit/taste-parent").get_data(as_text=True)

        self.assertIn('/dev/taste-evolution/taste-child', child_body)
        self.assertNotIn('/dev/taste-evolution/taste-parent', parent_body)

    def test_customer_facing_pages_do_not_expose_taste_evolution(self):
        for path in ("/", "/baby", "/results/session/taste-child"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("/dev/taste-evolution/", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
