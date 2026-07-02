import os
import tempfile
import unittest

from app import create_app, make_session_id
from namengine.core import (
    build_reaction,
    build_taste_profile,
    get_session_snapshot,
    refine_session,
    save_reaction,
)
from namengine.verticals import PET


class PhaseNineTasteProfileTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        self.tempdir.cleanup()

    def _seed_round_one(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
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
        self.assertEqual(profile.loved_names, ["Milo"])
        self.assertEqual(profile.rejected_names, ["Juniper"])
        self.assertIn("Strongest signal: Milo.", profile.summary)
        self.assertIsNotNone(snapshot["taste_profile"])

    def test_react_api_returns_refreshed_taste_profile(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.post(
            "/api/react",
            json={"session_id": session_id, "result_id": "pet-1", "value": "love"},
        )

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["taste_profile"]["loved_names"], ["Milo"])
        self.assertIn("Strongest signal: Milo.", data["taste_profile"]["summary"])

    def test_results_reload_shows_existing_taste_profile(self):
        session_id = self._seed_round_one()
        build_taste_profile(session_id)

        response = self.client.get("/pet/results?species=Dog&personality=Gentle&style=Warm")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Taste profile", body)
        self.assertIn("Strongest signal: Milo.", body)

    def test_refinement_uses_profile_summary(self):
        session_id = self._seed_round_one()

        _, _, results = refine_session(session_id, PET, instruction="warmer")

        self.assertIn("Strongest signal: Milo.", results[0].why_this_name)

    def test_compare_shows_taste_profile(self):
        session_id = self._seed_round_one()
        build_taste_profile(session_id)

        response = self.client.get(f"/compare/{session_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Taste profile", body)
        self.assertIn("Strongest signal: Milo.", body)


if __name__ == "__main__":
    unittest.main()
