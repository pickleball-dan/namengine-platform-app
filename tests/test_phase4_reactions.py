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

    def test_react_api_returns_reaction_payload(self):
        query = b"species=Dog&personality=Gentle&style=Warm"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")
        response = self.client.post(
            "/api/react",
            json={
                "session_id": session_id,
                "result_id": "pet-1",
                "value": "maybe",
            },
        )

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["reaction"]["session_id"], session_id)
        self.assertEqual(data["reaction"]["result_id"], "pet-1")
        self.assertEqual(data["reaction"]["value"], "maybe")

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
        self.assertIn("/static/js/reactions.js", body)


if __name__ == "__main__":
    unittest.main()
