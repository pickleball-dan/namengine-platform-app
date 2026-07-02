import os
import tempfile
import unittest

from app import create_app
from namengine.core import build_brief, build_trust_cue, generate_names
from namengine.verticals import PET


class PhaseFourteenProgressExperienceTest(unittest.TestCase):
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

    def test_intake_page_has_progress_experience(self):
        response = self.client.get("/pet")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("data-progress-form", body)
        self.assertIn("NamEngine is working", body)
        self.assertIn("Checking fit and callability", body)
        self.assertIn("js/progress.js", body)

    def test_results_page_has_trust_cue_and_refine_progress(self):
        response = self.client.get("/pet/results?species=Dog&personality=Gentle&style=Warm")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Selected from", body)
        self.assertIn("Matched to your brief", body)
        self.assertIn("data-progress-form", body)
        self.assertIn("Comparing naming strategies", body)

    def test_trust_cue_summarizes_validation_work(self):
        brief = build_brief(PET, {"species": "Dog", "style": "Warm"})
        names = generate_names(PET, brief)

        cue = build_trust_cue(names)

        self.assertEqual(cue["candidate_count"], 8)
        self.assertGreater(cue["validation_count"], 0)
        self.assertIn("callability", cue["traits"])
        self.assertIn("Selected from 8 candidates", cue["summary"])

    def test_progress_copy_hides_provider_plumbing(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True).lower()

        self.assertNotIn("openai", body)
        self.assertNotIn("claude", body)
        self.assertNotIn("gemini", body)
        self.assertNotIn("groq", body)


if __name__ == "__main__":
    unittest.main()
