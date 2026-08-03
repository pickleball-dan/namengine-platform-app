import os
import tempfile
import unittest

from app import _query_string_from_mapping, _sanitize_intake_source, create_app, make_session_id
from access_helpers import unlock_beta_access
from namengine.verticals import PET


class PhaseSeventeenNameDetailTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_ai_verticals = os.environ.get("NAMENGINE_AI_PRIMARY_VERTICALS")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = "none"
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def _pet_session_id_for_query(self, query: bytes) -> str:
        source = dict(pair.split("=", 1) for pair in query.decode("utf-8").split("&"))
        source = {key: value.replace("+", " ") for key, value in source.items()}
        sanitized = _sanitize_intake_source(PET, source)
        return make_session_id("pet", _query_string_from_mapping(sanitized).encode("utf-8"))

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_ai_verticals is None:
            os.environ.pop("NAMENGINE_AI_PRIMARY_VERTICALS", None)
        else:
            os.environ["NAMENGINE_AI_PRIMARY_VERTICALS"] = self.previous_ai_verticals
        self.tempdir.cleanup()

    def test_name_detail_route_restores_legacy_detail_path(self):
        query = b"pet_type=Dog&style=Classic&vibe=Playful"
        session_id = self._pet_session_id_for_query(query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        unlock_beta_access(self.client, "pet")

        response = self.client.get(f"/pet/name/{session_id}/pet-1")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Name detail", body)
        self.assertIn("Milo", body)
        self.assertIn("Why this name?", body)
        self.assertIn("Best fit", body)
        self.assertIn("Worth noting", body)
        self.assertNotIn("Watch-outs", body)
        self.assertIn("Validation", body)
        self.assertIn("Choose Milo", body)
        self.assertIn("Compare favorites", body)
        self.assertIn("Back to results", body)
        self.assertNotIn("Adjust direction", body)
        self.assertNotIn('/pet?', body)

    def test_name_detail_rejects_wrong_vertical(self):
        query = b"pet_type=Dog&style=Classic&vibe=Playful"
        session_id = self._pet_session_id_for_query(query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.get(f"/baby/name/{session_id}/pet-1")

        self.assertEqual(response.status_code, 404)

    def test_name_detail_rejects_missing_result(self):
        query = b"pet_type=Dog&style=Classic&vibe=Playful"
        session_id = self._pet_session_id_for_query(query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.get(f"/pet/name/{session_id}/missing")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
