import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from namengine.core import build_brief, generate_names
from namengine.core.schemas import NameResult
from namengine.verticals import BABY, PET


class PhaseThreePetResultsTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        env_patch = patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "",
                "NAMENGINE_DB_PATH": os.path.join(self.tempdir.name, "phase3.sqlite3"),
            },
            clear=False,
        )
        env_patch.start()
        self.addCleanup(env_patch.stop)
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def test_build_brief_normalizes_pet_query_inputs(self):
        brief = build_brief(
            PET,
            {
                "pet_type": "Dog",
                "vibe": "Gentle and goofy",
                "style": "Warm but not too cute",
                "avoid": "Spot, Killer",
            },
        )

        self.assertEqual(brief.vertical, "pet")
        self.assertEqual(brief.inputs["pet_type"], "Dog")
        self.assertEqual(brief.inputs["species"], "Dog")
        self.assertEqual(brief.avoid, ["Spot", "Killer"])

    def test_build_brief_keeps_legacy_pet_query_inputs(self):
        brief = build_brief(
            PET,
            {
                "species": "Dog",
                "personality": "Gentle and goofy",
                "style": "Warm but not too cute",
            },
        )

        self.assertEqual(brief.inputs["pet_type"], "Dog")
        self.assertEqual(brief.inputs["vibe"], "Gentle and goofy")

    def test_pet_generator_returns_shared_name_results(self):
        brief = build_brief(
            PET,
            {
                "species": "Dog",
                "personality": "loyal",
                "style": "warm",
            },
        )

        results = generate_names(PET, brief)

        self.assertEqual(len(results), 8)
        self.assertIsInstance(results[0], NameResult)
        self.assertEqual(results[0].metadata["source"], "phase3_fallback")
        self.assertGreaterEqual(len(results[0].validation), 2)

    def test_pet_fallback_explanations_are_name_specific(self):
        brief = build_brief(PET, {"pet_type": "Dog", "vibe": "Playful", "style": "Classic"})

        results = generate_names(PET, brief, use_ai=False)
        explanations = {result.name: result.why_this_name for result in results}

        self.assertIn("bright repeated sounds", explanations["Rory"])
        self.assertIn("friendly, rounded sound", explanations["Ollie"])
        self.assertNotEqual(explanations["Rory"], explanations["Ollie"])

    def test_pet_results_route_renders_name_cards(self):
        response = self.client.get(
            "/pet/results?species=Dog&personality=Gentle&style=Warm&avoid=Spot"
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Pet names shaped from your taste", body)
        self.assertIn("Rosie", body)
        self.assertIn("Why this feels like them", body)
        self.assertIn("Love", body)
        self.assertNotIn('data-reaction-value="maybe"', body)
        self.assertIn("No", body)
        self.assertIn("Your direction", body)
        self.assertIn("<dt>Pet</dt>", body)
        self.assertIn("<dt>Personality</dt>", body)
        self.assertIn("Open full detail", body)
        self.assertIn("/pet/name/", body)
        self.assertNotIn("<dt>Species</dt>", body)

    def test_baby_results_route_renders_name_cards(self):
        response = self.client.get(
            "/baby/results?gender=Girl&style=Classic&family_context=Last+name+Parker"
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Here’s what stood out", body)
        self.assertIn("Eloise", body)
        self.assertIn("Pronunciation", body)
        self.assertIn("Love", body)
        self.assertNotIn('data-reaction-value="maybe"', body)
        self.assertIn("No", body)
        self.assertIn("Your direction", body)
        self.assertIn("<dt>Gender</dt>", body)
        self.assertIn("<dt>Style</dt>", body)
        self.assertIn("Explore <", body)
        self.assertIn("/baby/name/", body)

    def test_baby_generator_returns_shared_name_results(self):
        brief = build_brief(
            BABY,
            {
                "gender": "Girl",
                "style": "Classic",
                "family_context": "Surname Parker",
            },
        )

        results = generate_names(BABY, brief, use_ai=False)

        self.assertEqual(len(results), 8)
        self.assertIsInstance(results[0], NameResult)
        self.assertEqual(results[0].metadata["source"], "baby_fallback")
        self.assertGreaterEqual(len(results[0].validation), 3)


if __name__ == "__main__":
    unittest.main()
