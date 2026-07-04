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

    def test_pet_intake_collects_portrait_details(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('name="pet_breed"', body)
        self.assertIn('name="pet_color"', body)
        self.assertIn('name="pet_life_stage"', body)
        self.assertIn("Young", body)
        self.assertIn("Mature", body)
        self.assertIn('data-other-select="pet_type_other"', body)
        self.assertIn('name="pet_type_other"', body)
        self.assertNotIn("Puppy", body)
        self.assertNotIn("Adult", body)
        self.assertNotIn("Senior", body)

    def test_pet_original_mode_exists_and_generates_original_results(self):
        response = self.client.get("/pet/original")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Original Pet Name Studio", body)
        self.assertIn("Letter to begin the name", body)
        self.assertIn('name="pet_breed"', body)
        self.assertIn('name="pet_color"', body)
        self.assertIn('name="pet_life_stage"', body)
        self.assertIn('data-other-select="pet_type_other"', body)
        self.assertIn('name="pet_type_other"', body)
        self.assertIn("Young or mature?", body)
        self.assertIn("Create original pet names", body)

        results = self.client.get(
            "/pet/original/results?pet_type=Dog&pet_breed=Whippet&pet_color=Blue+gray"
            "&pet_life_stage=Mature&style=Modern&vibe=Playful&starting_letter=L"
        )
        results_body = results.get_data(as_text=True)

        self.assertEqual(results.status_code, 200)
        self.assertIn("Original pet names shaped from your life", results_body)
        self.assertIn("Lumo", results_body)

    def test_other_pet_type_custom_value_is_used_for_results(self):
        response = self.client.get(
            "/pet/results?pet_type=Other&pet_type_other=Goat&style=Classic&vibe=Playful"
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("<dt>Pet</dt>", body)
        self.assertIn("<dd>Goat</dd>", body)
        self.assertNotIn("<dd>Other</dd>", body)

    def test_original_other_pet_type_redirects_with_custom_value(self):
        response = self.client.post(
            "/pet/original/results",
            data={
                "pet_type": "Other",
                "pet_type_other": "Goat",
                "style": "Modern",
                "vibe": "Playful",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("pet_type=Goat", response.headers["Location"])
        self.assertNotIn("pet_type_other", response.headers["Location"])

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

    def test_original_shared_shortlist_route_renders_saved_session(self):
        query = (
            b"pet_type=Dog&pet_breed=Whippet&pet_color=Blue+gray"
            b"&pet_life_stage=Mature&style=Modern&vibe=Playful&starting_letter=L"
        )
        session_id = make_session_id("pet-original", query)
        self.client.get(f"/pet/original/results?{query.decode('utf-8')}")

        response = self.client.get(f"/share/{session_id}")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Shared NamEngine Pet list", body)
        self.assertIn("Lumo", body)

    def test_missing_shared_shortlist_route_has_recovery_page(self):
        response = self.client.get("/share/pet-original-missing")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 410)
        self.assertIn("This saved list is no longer available.", body)
        self.assertIn("Start a new pet list", body)
        self.assertNotIn("Not Found", body)

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
