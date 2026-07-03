import os
import tempfile
import unittest
from pathlib import Path

from app import create_app, make_session_id


class PhaseEighteenPetLegacyParityTest(unittest.TestCase):
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

    def test_pet_uses_real_legacy_logo_assets(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("images/pet/namengine-pet-logo-transparent.png", body)
        self.assertIn("images/pet/namengine-pet-card-share-v3.jpg", body)
        self.assertIn("vertical-page-logo", body)

    def test_pet_original_mode_exists_and_generates_original_results(self):
        response = self.client.get("/pet/original")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Original Pet Name Studio", body)
        self.assertIn("Letter to begin the name", body)
        self.assertIn("Create original pet names", body)

        results = self.client.get(
            "/pet/original/results?pet_type=Dog&style=Modern&vibe=Playful&starting_letter=L"
        )
        results_body = results.get_data(as_text=True)

        self.assertEqual(results.status_code, 200)
        self.assertIn("Original pet names shaped from your life", results_body)
        self.assertIn("Lumo", results_body)

    def test_results_have_share_route_and_reaction_images(self):
        response = self.client.get("/pet/results?pet_type=Dog&style=Classic&vibe=Playful")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("/share/pet-", body)
        self.assertIn("images/reactions/love.jpg", body)
        self.assertIn("images/reactions/maybe.jpg", body)
        self.assertIn("images/reactions/no.jpg", body)
        self.assertNotIn(">Love</button>", body)
        self.assertNotIn(">Maybe</button>", body)
        self.assertNotIn(">No</button>", body)

    def test_shared_shortlist_route_renders_saved_session(self):
        query = b"pet_type=Dog&style=Classic&vibe=Playful"
        session_id = make_session_id("pet", query)
        self.client.get(f"/pet/results?{query.decode('utf-8')}")

        response = self.client.get(f"/share/{session_id}")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Shared NamEngine Pet list", body)
        self.assertIn("Start your own list", body)
        self.assertIn("Open detail", body)

    def test_feedback_route_renders_and_accepts_submission(self):
        response = self.client.get("/feedback")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Beta feedback", response.get_data(as_text=True))

        submitted = self.client.post("/feedback", data={"overall_rating": "Promising"})
        self.assertEqual(submitted.status_code, 200)
        self.assertIn("Feedback received", submitted.get_data(as_text=True))
        feedback_path = Path(self.db_path).parent / "feedback.jsonl"
        self.assertTrue(feedback_path.is_file())
        self.assertIn("Promising", feedback_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
