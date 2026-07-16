import unittest

from app import create_app, make_session_id
from namengine.core import ReactionError, build_reaction
from namengine.core.schemas import ReactionValue


class PhaseFourReactionTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def test_build_reaction_returns_shared_reaction(self):
        reaction = build_reaction("pet-session", "pet-1", "love")

        self.assertEqual(reaction.session_id, "pet-session")
        self.assertEqual(reaction.result_id, "pet-1")
        self.assertEqual(reaction.value, ReactionValue.LOVE)

    def test_build_reaction_rejects_invalid_value(self):
        with self.assertRaises(ReactionError):
            build_reaction("pet-session", "pet-1", "trendy")

    def test_react_api_accepts_love_and_no(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        for result_id, value in (("pet-1", "love"), ("pet-2", "no")):
            response = self.client.post(
                "/api/react",
                json={"session_id": session_id, "result_id": result_id, "value": value},
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.get_json()["reaction"]["value"], value)

    def test_react_api_rejects_new_maybe_submission(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.post(
            "/api/react",
            json={"session_id": session_id, "result_id": "pet-1", "value": "maybe"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("love, no", response.get_json()["error"])

    def test_legacy_builder_still_reads_maybe(self):
        reaction = build_reaction("legacy-session", "pet-1", "maybe")

        self.assertEqual(reaction.value, ReactionValue.MAYBE)

    def test_react_api_rejects_missing_session(self):
        response = self.client.post(
            "/api/react",
            json={"result_id": "pet-1", "value": "love"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("session_id is required", response.get_json()["error"])

    def test_results_page_has_reaction_metadata(self):
        response = self.client.get(
            "/pet/results?species=Dog&personality=Gentle&style=Warm"
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('data-session-id="pet-', body)
        self.assertIn('data-result-id="pet-1"', body)
        self.assertIn('data-reaction-value="love"', body)
        self.assertIn('data-reaction-value="no"', body)
        self.assertNotIn('data-reaction-value="maybe"', body)
        self.assertIn("/static/js/reactions.js", body)


if __name__ == "__main__":
    unittest.main()
