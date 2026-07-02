import os
import tempfile
import unittest

from app import create_app, make_session_id
from namengine.core import (
    build_reaction,
    build_reaction_effect_summary,
    get_session_snapshot,
    refine_session,
    save_reaction,
)
from namengine.verticals import PET


class PhaseSevenRefinementTest(unittest.TestCase):
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

    def test_reaction_effect_summary_is_short_and_directional(self):
        session_id = self._seed_round_one()
        snapshot = get_session_snapshot(session_id)

        summary = build_reaction_effect_summary(snapshot)

        self.assertIn("We leaned toward Milo.", summary)
        self.assertIn("We moved away from Juniper.", summary)

    def test_refine_session_creates_round_two_child(self):
        session_id = self._seed_round_one()

        child_session_id, brief, results = refine_session(
            session_id,
            PET,
            instruction="shorter and warmer",
        )
        child = get_session_snapshot(child_session_id)

        self.assertEqual(child["session"]["round_number"], 2)
        self.assertEqual(child["session"]["parent_session_id"], session_id)
        self.assertEqual(child["session"]["refinement_prompt"], "shorter and warmer")
        self.assertEqual(len(results), 8)
        self.assertIn("Milo", brief.liked_examples)
        self.assertIn("Juniper", brief.rejected_examples)

    def test_refine_route_renders_round_two(self):
        session_id = self._seed_round_one()
        response = self.client.post(
            "/refine",
            data={"session_id": session_id, "instruction": "shorter"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Round 2", body)
        self.assertNotIn("Get finalists", body)
        self.assertIn("Ready for a fresh list?", body)
        self.assertIn("Generate New List", body)
        self.assertIn("Benny", body)

    def test_results_page_has_bottom_generate_new_list_action(self):
        session_id = self._seed_round_one()
        response = self.client.get("/pet/results?species=Dog&personality=Gentle&style=Warm")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="bottom-next-panel"', body)
        self.assertIn("Ready for a fresh list?", body)
        self.assertIn("Generate New List", body)
        self.assertIn(f'name="session_id" value="{session_id}"', body)
        self.assertIn('action="/refine"', body)

    def test_round_three_returns_finalists(self):
        session_id = self._seed_round_one()
        round_two_id, _, _ = refine_session(session_id, PET, instruction="shorter")
        save_reaction(build_reaction(round_two_id, "pet-1", "love"))

        round_three_id, _, results = refine_session(round_two_id, PET, instruction="finalists")
        round_three = get_session_snapshot(round_three_id)

        self.assertEqual(round_three["session"]["round_number"], 3)
        self.assertEqual(round_three["session"]["parent_session_id"], round_two_id)
        self.assertEqual(len(results), 6)

    def test_refine_route_rejects_missing_session(self):
        response = self.client.post("/refine", data={"session_id": "missing"})

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
