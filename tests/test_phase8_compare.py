import os
import tempfile
import unittest

from app import create_app, make_session_id
from namengine.core import (
    build_compare_items,
    build_reaction,
    get_session_snapshot,
    refine_session,
    save_reaction,
)
from namengine.verticals import PET


class PhaseEightCompareTest(unittest.TestCase):
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

    def _seed_chain(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        save_reaction(build_reaction(session_id, "pet-1", "love"))
        save_reaction(build_reaction(session_id, "pet-2", "no"))
        round_two_id, _, _ = refine_session(session_id, PET, instruction="shorter")
        save_reaction(build_reaction(round_two_id, "pet-1", "love"))
        save_reaction(build_reaction(round_two_id, "pet-2", "maybe"))
        return session_id, round_two_id

    def test_compare_items_include_loved_names_across_chain(self):
        _, round_two_id = self._seed_chain()

        items = build_compare_items(round_two_id)
        names = [item["name"] for item in items]

        self.assertIn("Milo", names)
        self.assertIn("Benny", names)
        self.assertLessEqual(len(items), 6)

    def test_compare_uses_maybe_as_backup(self):
        query = b"species=Cat&personality=Quiet&style=Soft"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        save_reaction(build_reaction(session_id, "pet-3", "maybe"))
        save_reaction(build_reaction(session_id, "pet-4", "maybe"))

        items = build_compare_items(session_id)

        self.assertGreaterEqual(len(items), 2)
        reactions = {item["reaction"] for item in items}
        self.assertIn("maybe", reactions)
        self.assertIn("finalist", reactions)

    def test_compare_route_renders_decision_page(self):
        _, round_two_id = self._seed_chain()
        response = self.client.get(f"/compare/{round_two_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Compare Favorites", body)
        self.assertIn("Best if", body)
        self.assertIn("Watch-out", body)
        self.assertIn("Choose with confidence", body)
        self.assertIn("Choose Milo", body)
        self.assertIn("Milo", body)
        self.assertIn("Benny", body)

    def test_compare_fills_with_latest_finalists(self):
        session_id, round_two_id = self._seed_chain()
        round_three_id, _, _ = refine_session(round_two_id, PET, instruction="finalists")

        items = build_compare_items(round_three_id)

        self.assertGreater(len(items), 2)
        self.assertIn("finalist", {item["reaction"] for item in items})
        self.assertLessEqual(len(items), 6)

    def test_results_page_links_to_compare(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        response = self.client.get(f"/pet/results?{query.decode('utf-8')}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(f"/compare/{session_id}", response.get_data(as_text=True))

    def test_compare_route_rejects_missing_session(self):
        response = self.client.get("/compare/missing")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
