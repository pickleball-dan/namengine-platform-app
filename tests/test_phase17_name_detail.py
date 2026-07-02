import os
import tempfile
import unittest

from app import create_app, make_session_id


class PhaseSeventeenNameDetailTest(unittest.TestCase):
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

    def test_name_detail_route_restores_legacy_detail_path(self):
        query = b"pet_type=Dog&style=Classic&vibe=Playful"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.get(f"/pet/name/{session_id}/pet-1")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Name detail", body)
        self.assertIn("Milo", body)
        self.assertIn("Why this name?", body)
        self.assertIn("Best fit", body)
        self.assertIn("Watch-outs", body)
        self.assertIn("Validation", body)
        self.assertIn("Choose Milo", body)
        self.assertIn("Compare favorites", body)
        self.assertIn("Back to results", body)
        self.assertIn("Adjust direction", body)

    def test_name_detail_rejects_wrong_vertical(self):
        query = b"pet_type=Dog&style=Classic&vibe=Playful"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.get(f"/baby/name/{session_id}/pet-1")

        self.assertEqual(response.status_code, 404)

    def test_name_detail_rejects_missing_result(self):
        query = b"pet_type=Dog&style=Classic&vibe=Playful"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.get(f"/pet/name/{session_id}/missing")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
