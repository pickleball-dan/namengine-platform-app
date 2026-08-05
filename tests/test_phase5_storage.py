import os
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

import app as platform_app
from app import create_app, make_session_id
from access_helpers import unlock_beta_access
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
from namengine.core.storage import connect, initialize_database
import namengine.core.storage as storage


class PhaseFiveStorageTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_ai_primary_verticals = os.environ.get("NAMENGINE_AI_PRIMARY_VERTICALS")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = "none"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_ai_primary_verticals is None:
            os.environ.pop("NAMENGINE_AI_PRIMARY_VERTICALS", None)
        else:
            os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = self.previous_ai_primary_verticals
        self.tempdir.cleanup()

    def test_connect_enables_foreign_keys_and_busy_timeout(self):
        with closing(connect()) as connection:
            foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
            busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]

        self.assertEqual(foreign_keys, 1)
        self.assertEqual(busy_timeout, 5000)

    def test_initialize_database_memoizes_per_existing_database_path(self):
        original_connect = storage.connect
        calls = []

        def counted_connect(db_path=None):
            calls.append(db_path)
            return original_connect(db_path)

        with patch.object(storage, "connect", side_effect=counted_connect):
            initialize_database()
            initialize_database()

        self.assertEqual(len(calls), 1)

    def test_initialize_database_supports_multiple_database_paths(self):
        other_db_path = os.path.join(self.tempdir.name, "other.sqlite3")

        initialize_database(self.db_path)
        initialize_database(other_db_path)

        self.assertTrue(os.path.exists(self.db_path))
        self.assertTrue(os.path.exists(other_db_path))

    def test_save_session_persists_brief_and_results(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)

        save_session("pet-session", "pet", brief, results)
        snapshot = get_session_snapshot("pet-session")

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["session"]["vertical"], "pet")
        self.assertEqual(len(snapshot["results"]), 8)
        self.assertEqual(snapshot["reaction_counts"], {"love": 0, "maybe": 0, "no": 0})

    def test_session_results_reuses_snapshot_reaction_counts(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)
        save_session("pet-session", "pet", brief, results)
        save_reaction(build_reaction("pet-session", "pet-1", "love"))
        unlock_beta_access(self.client, "pet")

        with patch.object(platform_app, "get_reaction_counts", side_effect=AssertionError("duplicate read")):
            response = self.client.get("/results/session/pet-session")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Love", body)

    def test_save_reaction_upserts_one_reaction_per_result(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        results = generate_names(PET, brief)
        save_session("pet-session", "pet", brief, results)

        save_reaction(build_reaction("pet-session", "pet-1", "love"))
        save_reaction(build_reaction("pet-session", "pet-1", "maybe"))

        self.assertEqual(get_reaction_counts("pet-session"), {"love": 0, "maybe": 1, "no": 0})

    def test_pet_results_route_persists_session(self):
        query = b"pet_type=Dog&vibe=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        response = self.client.get(f"/pet/results?{query.decode('utf-8')}")

        self.assertEqual(response.status_code, 200)
        snapshot = get_session_snapshot(session_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(len(snapshot["results"]), 8)

    def test_react_api_persists_reaction_and_returns_counts(self):
        query = b"pet_type=Dog&vibe=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        unlock_beta_access(self.client, "pet")
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
