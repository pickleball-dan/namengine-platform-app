import os
import tempfile
import unittest

from app import create_app, make_session_id
from namengine.core import (
    build_brief,
    build_reaction,
    generate_names,
    get_reaction_counts,
    get_session_snapshot,
    save_reaction,
    save_session,
)
from namengine.verticals import PET


class PhaseFiveStorageTest(unittest.TestCase):
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

    def test_save_session_persists_brief_and_results(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)

        save_session("pet-session", "pet", brief, results)
        snapshot = get_session_snapshot("pet-session")

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["session"]["vertical"], "pet")
        self.assertEqual(len(snapshot["results"]), 8)
        self.assertEqual(snapshot["reaction_counts"], {"love": 0, "maybe": 0, "no": 0})

    def test_save_reaction_upserts_one_reaction_per_result(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)
        save_session("pet-session", "pet", brief, results)

        save_reaction(build_reaction("pet-session", "pet-1", "love"))
        save_reaction(build_reaction("pet-session", "pet-1", "maybe"))

        self.assertEqual(get_reaction_counts("pet-session"), {"love": 0, "maybe": 1, "no": 0})

    def test_pet_results_route_persists_session(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        response = self.client.get(f"/pet/results?{query.decode('utf-8')}")

        self.assertEqual(response.status_code, 200)
        snapshot = get_session_snapshot(session_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(len(snapshot["results"]), 8)

    def test_react_api_persists_reaction_and_returns_counts(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        response = self.client.post(
            "/api/react",
            json={
                "session_id": session_id,
                "result_id": "pet-1",
                "value": "love",
            },
        )

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["reaction_counts"], {"love": 1, "maybe": 0, "no": 0})
        self.assertEqual(get_reaction_counts(session_id), {"love": 1, "maybe": 0, "no": 0})

    def test_react_api_rejects_unknown_session_result(self):
        response = self.client.post(
            "/api/react",
            json={
                "session_id": "missing-session",
                "result_id": "pet-1",
                "value": "love",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("session/result not found", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
