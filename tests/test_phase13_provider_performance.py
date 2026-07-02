import os
import tempfile
import unittest

from app import create_app, make_session_id
from namengine.core import (
    build_provider_performance,
    build_reaction,
    get_provider_performance,
    get_session_snapshot,
    refresh_provider_performance,
    save_chosen_name,
    save_reaction,
)


class PhaseThirteenProviderPerformanceTest(unittest.TestCase):
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

    def _seed_session(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        return session_id

    def test_build_provider_performance_from_snapshot(self):
        session_id = self._seed_session()
        save_reaction(build_reaction(session_id, "pet-1", "love"))
        save_reaction(build_reaction(session_id, "pet-2", "maybe"))
        save_reaction(build_reaction(session_id, "pet-3", "no"))
        save_chosen_name(session_id, "pet-1")

        snapshot = get_session_snapshot(session_id)
        performance = build_provider_performance(snapshot)

        self.assertEqual(len(performance), 1)
        self.assertEqual(performance[0].provider, "fallback")
        self.assertEqual(performance[0].generated_count, 8)
        self.assertEqual(performance[0].love_count, 1)
        self.assertEqual(performance[0].chosen_count, 1)
        self.assertGreater(performance[0].performance_score, 0)

    def test_save_reaction_refreshes_provider_performance(self):
        session_id = self._seed_session()

        save_reaction(build_reaction(session_id, "pet-1", "love"))
        rows = get_provider_performance(session_id)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["provider"], "fallback")
        self.assertEqual(rows[0]["love_count"], 1)
        self.assertGreater(rows[0]["love_rate"], 0)

    def test_save_chosen_refreshes_provider_performance(self):
        session_id = self._seed_session()

        save_chosen_name(session_id, "pet-1")
        rows = get_provider_performance(session_id)

        self.assertEqual(rows[0]["chosen_count"], 1)
        self.assertGreater(rows[0]["choose_rate"], 0)

    def test_refresh_provider_performance_returns_rows(self):
        session_id = self._seed_session()

        rows = refresh_provider_performance(session_id)

        self.assertEqual(rows[0]["provider"], "fallback")
        self.assertEqual(rows[0]["generated_count"], 8)
        self.assertIn("performance_score", rows[0])

    def test_session_snapshot_includes_provider_performance(self):
        session_id = self._seed_session()
        save_reaction(build_reaction(session_id, "pet-1", "love"))

        snapshot = get_session_snapshot(session_id)

        self.assertEqual(snapshot["provider_performance"][0]["provider"], "fallback")


if __name__ == "__main__":
    unittest.main()
