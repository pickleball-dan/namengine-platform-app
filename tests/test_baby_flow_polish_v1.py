import os
import tempfile
import unittest
from pathlib import Path

from app import create_app


class BabyFlowPolishV1Test(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_openai_key = os.environ.get("OPENAI_API_KEY")
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self.tempdir.name, "baby-flow-polish.sqlite3")
        os.environ.pop("OPENAI_API_KEY", None)
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_openai_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self.previous_openai_key
        self.tempdir.cleanup()

    def test_baby_intake_opens_with_an_emotional_welcome(self):
        response = self.client.get("/baby")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Let’s discover your child’s name together.", body)
        self.assertIn("Most parents finish in about 3–5 minutes.", body)
        self.assertIn('class="button-link baby-begin-button" href="#baby-intake-form">Begin</a>', body)
        self.assertIn('id="baby-intake-form"', body)
        self.assertIn('action="/baby/feelings"', body)
        welcome = body.split('<div class="baby-welcome">', 1)[1].split('<div class="hero-actions">', 1)[0]
        self.assertNotIn("vertical-page-logo", welcome)

    def test_baby_intake_keeps_questions_and_trust_contract(self):
        response = self.client.get("/baby")
        body = response.get_data(as_text=True)

        self.assertIn("Tell us what matters to your family.", body)
        self.assertIn("About your baby", body)
        self.assertIn("Name style", body)
        self.assertIn("Fit and feeling", body)
        self.assertIn("Thoughtful AI guidance", body)
        self.assertIn("Your family’s story stays private", body)
        self.assertIn("You’re always in control", body)
        self.assertNotIn("About your baby. Step 1 of 3", body)
        self.assertEqual(body.count("data-baby-journey-stage"), 3)
        self.assertIn("Your evolving taste", body)
        self.assertIn("Every name you love helps NamEngine", body)

    def test_baby_feelings_step_uses_guided_copy_without_route_changes(self):
        response = self.client.get("/baby/feelings?gender=Girl&style=Classic&sound=Soft")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("What should guide the search?", body)
        self.assertIn("Skip for now", body)
        self.assertIn('data-baby-final-skip', body)
        self.assertIn('action="/baby/results"', body)

    def test_baby_results_emphasize_understanding_names_and_saves(self):
        response = self.client.get("/baby/results?gender=Girl&style=Classic&sound=Soft")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Based on everything you’ve shared", body)
        self.assertIn("baby-saved-progress", body)
        self.assertIn("You’ve loved 0 names in this round so far", body)
        self.assertIn("refine your next recommendations", body)
        self.assertIn("result-explore-link", body)
        self.assertIn("Love it", body)
        self.assertIn("Not for us", body)
        self.assertIn("Why this fits your family", body)
        self.assertIn("baby-result-tags", body)

    def test_baby_progress_and_saved_state_have_frontend_contracts(self):
        root = Path(self.app.root_path)
        progress = (root / "static" / "js" / "progress.js").read_text(encoding="utf-8")
        reactions = (root / "static" / "js" / "reactions.js").read_text(encoding="utf-8")
        intake_polish = (root / "static" / "js" / "baby-intake-polish.js").read_text(encoding="utf-8")
        css = (root / "static" / "css" / "platform.css").read_text(encoding="utf-8")

        self.assertIn("Interpreting your naming taste", progress)
        self.assertIn("Building a broader candidate pool", progress)
        self.assertIn("Rejecting weaker fits before we show you finalists", progress)
        self.assertIn("Shaping the shortlist", progress)
        self.assertIn('visualLabel.textContent = "Family fit"', progress)
        self.assertIn("[data-saved-count]", reactions)
        self.assertIn("is-complete", intake_polish)
        self.assertIn("Building your naming profile", intake_polish)
        self.assertIn("650", intake_polish)
        self.assertIn(".vertical-baby .baby-welcome", css)
        self.assertIn(".vertical-baby .baby-intake-form .field select", css)
        self.assertIn(".vertical-baby .result-card h2", css)


if __name__ == "__main__":
    unittest.main()
