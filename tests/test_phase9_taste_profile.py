import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, make_session_id
from namengine.core import (
    NameResult,
    build_brief,
    build_generation_prompt,
    build_reaction,
    build_taste_profile,
    get_session_snapshot,
    refine_session,
    save_reaction,
    save_session,
)
from namengine.verticals import PET


class PhaseNineTasteProfileTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_openai_key = os.environ.get("OPENAI_API_KEY")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        os.environ["OPENAI_API_KEY"] = ""
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_openai_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self.previous_openai_key
        self.tempdir.cleanup()

    def _seed_round_one(self):
        query = b"pet_type=Dog&vibe=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        save_reaction(build_reaction(session_id, "pet-1", "love"))
        save_reaction(build_reaction(session_id, "pet-2", "no"))
        return session_id

    def test_build_taste_profile_from_reactions(self):
        session_id = self._seed_round_one()

        profile = build_taste_profile(session_id)
        snapshot = get_session_snapshot(session_id)

        self.assertEqual(profile.session_id, session_id)
        self.assertEqual(profile.loved_names, ["Rosie"])
        self.assertEqual(profile.rejected_names, ["Juniper"])
        self.assertIn("Strongest signal: Rosie.", profile.summary)
        self.assertIsNotNone(snapshot["taste_profile"])

    def test_build_taste_profile_uses_ai_metadata_for_reacted_names(self):
        session_id = "pet-ai-metadata-session"
        brief = build_brief(PET, {"species": "Dog", "personality": "Gentle", "style": "Warm"})
        save_session(
            session_id,
            "pet",
            brief,
            [
                NameResult(
                    id="pet-1",
                    name="Rosie",
                    slug="rosie",
                    tags=["friendly"],
                    scores={"callability": 0.92},
                    metadata={
                        "candidate_pool": [
                            {
                                "name": "Rosie",
                                "territory": "warm-callable",
                                "rationale": "Soft, familiar warmth with an easy call shape.",
                                "tags": ["soft-friendly"],
                            }
                        ],
                        "taste_strategy": {
                            "taste_thesis": "Warm, bright, easy-to-call pet names.",
                            "soft_preferences": ["compact warmth"],
                        },
                    },
                ),
                NameResult(
                    id="pet-2",
                    name="Juniper",
                    slug="juniper",
                    tags=["botanical"],
                    metadata={
                        "candidate_pool": [
                            {
                                "name": "Juniper",
                                "territory": "woodland-whimsical",
                                "rationale": "Botanical and more whimsical than requested.",
                                "tags": ["nature-whimsy"],
                            }
                        ]
                    },
                ),
            ],
        )
        save_reaction(build_reaction(session_id, "pet-1", "love"))
        save_reaction(build_reaction(session_id, "pet-2", "no"))

        profile = build_taste_profile(session_id)
        prompt = build_generation_prompt(
            vertical=PET,
            brief=brief,
            round_number=2,
            taste_profile=profile,
            previous_names=["Rosie", "Juniper"],
            count=8,
            taste_strategy={"taste_thesis": "Refine from reactions."},
            prompt_version="test-prompt-version",
        )

        self.assertEqual(profile.liked_territories, ["warm-callable"])
        self.assertEqual(profile.disliked_territories, ["woodland-whimsical"])
        self.assertIn("Soft, familiar warmth", profile.liked_rationales[0])
        self.assertIn("Botanical", profile.disliked_rationales[0])
        self.assertIn("soft-friendly", profile.style_preferences)
        self.assertIn("nature-whimsy", profile.rejected_lanes)
        self.assertEqual(prompt["taste_profile"]["liked_territories"], ["warm-callable"])
        self.assertEqual(prompt["taste_profile"]["disliked_territories"], ["woodland-whimsical"])
        self.assertIn("Soft, familiar warmth", prompt["taste_profile"]["liked_rationales"][0])
        self.assertIn("Botanical", prompt["taste_profile"]["disliked_rationales"][0])
        self.assertNotIn("maybe_names", prompt["taste_profile"])

    def test_react_api_returns_refreshed_taste_profile(self):
        query = b"pet_type=Dog&vibe=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        with patch("app.beta_unlocked_from_request", return_value=True):
            response = self.client.post(
                "/api/react",
                json={"session_id": session_id, "result_id": "pet-1", "value": "love"},
            )

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["taste_profile"]["loved_names"], ["Rosie"])
        self.assertIn("Strongest signal: Rosie.", data["taste_profile"]["summary"])

    def test_results_reload_shows_existing_taste_profile(self):
        session_id = self._seed_round_one()
        build_taste_profile(session_id)

        response = self.client.get("/pet/results?pet_type=Dog&vibe=Gentle&style=Warm")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Taste profile", body)
        self.assertIn("Strongest signal: Rosie.", body)

    def test_refinement_uses_profile_summary(self):
        session_id = self._seed_round_one()

        _, _, results = refine_session(session_id, PET, instruction="warmer")

        self.assertIn("Strongest signal: Rosie.", results[0].why_this_name)

    def test_compare_shows_taste_profile(self):
        session_id = self._seed_round_one()
        build_taste_profile(session_id)

        with patch("app.beta_unlocked_from_request", return_value=True):
            response = self.client.get(f"/compare/{session_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Taste profile", body)
        self.assertIn("Strongest signal: Rosie.", body)


if __name__ == "__main__":
    unittest.main()

