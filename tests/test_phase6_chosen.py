import os
import tempfile
import unittest

from app import create_app, make_session_id
from namengine.core import (
    build_brief,
    generate_names,
    get_chosen_snapshot,
    get_session_snapshot,
    save_chosen_name,
    save_session,
)
from namengine.verticals import PET


class PhaseSixChosenNameTest(unittest.TestCase):
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

    def test_save_chosen_name_persists_choice(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)
        save_session("pet-session", "pet", brief, results)

        chosen = save_chosen_name("pet-session", "pet-1")
        snapshot = get_chosen_snapshot(chosen.id)

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["chosen"]["name"], "Milo")
        self.assertEqual(snapshot["chosen"]["vertical"], "pet")
        self.assertEqual(snapshot["result"]["name"], "Milo")

    def test_choose_route_redirects_to_chosen_page(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.post(
            "/choose",
            data={"session_id": session_id, "result_id": "pet-1"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/chosen/chosen-", response.headers["Location"])

    def test_chosen_page_renders_single_name(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        response = self.client.post(
            "/choose",
            data={"session_id": session_id, "result_id": "pet-1"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Milo", body)
        self.assertIn("Why this name?", body)
        self.assertIn("share-preview", body)
        self.assertIn("Meet Milo", body)
        self.assertIn("images/pet/namengine-pet-logo-transparent.png", body)
        self.assertIn("Copy link", body)
        self.assertIn("Start another", body)

    def test_session_stores_round_metadata(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)
        save_session(
            "pet-round-2",
            "pet",
            brief,
            results,
            round_number=2,
            parent_session_id="pet-round-1",
            refinement_prompt="More like Milo",
        )

        snapshot = get_session_snapshot("pet-round-2")

        self.assertEqual(snapshot["session"]["round_number"], 2)
        self.assertEqual(snapshot["session"]["parent_session_id"], "pet-round-1")
        self.assertEqual(snapshot["session"]["refinement_prompt"], "More like Milo")


if __name__ == "__main__":
    unittest.main()
