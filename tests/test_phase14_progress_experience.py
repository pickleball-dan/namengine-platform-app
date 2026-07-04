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
        self.assertIn("Building a shortlist around this identity", body)
        self.assertIn("A few quick checks before the list appears.", body)
        self.assertIn("Finding names for this identity", body)
        self.assertIn("Checking sound and use", body)
        self.assertIn("data-progress-visual", body)
        self.assertIn("progress-node-center", body)
        self.assertIn("Identity fit", body)
        self.assertIn("data-progress-headline", body)
        self.assertIn("js/progress.js", body)
        self.assertIn("novalidate", body)

    def test_results_page_has_trust_cue_and_refine_progress(self):
        response = self.client.get("/pet/results?species=Dog&personality=Gentle&style=Warm")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("8 names checked for fit, sound, and distinctiveness", body)
        self.assertIn("React to the names below", body)
        self.assertIn("next-step panel at the bottom", body)
        self.assertIn("data-progress-form", body)
        self.assertIn("Picking the strongest names", body)

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

    def test_progress_script_guides_missing_required_fields(self):
        script_path = os.path.join(self.app.static_folder, "js", "progress.js")
        with open(script_path, encoding="utf-8") as script_file:
            script = script_file.read()

        self.assertIn("form.checkValidity()", script)
        self.assertIn("focusFirstInvalid", script)
        self.assertIn("is-required-missing", script)
        self.assertIn("Required before we can generate names.", script)
        self.assertIn("scrollIntoView", script)

    def test_progress_script_holds_overlay_for_minimum_marketing_moment(self):
        script_path = os.path.join(self.app.static_folder, "js", "progress.js")
        with open(script_path, encoding="utf-8") as script_file:
            script = script_file.read()

        self.assertIn("minimumProgressMs = 10000", script)
        self.assertIn("event.preventDefault()", script)
        self.assertIn("setTimeout", script)
        self.assertIn("requestForForm(form, event.submitter)", script)
        self.assertIn("fetch(url", script)
        self.assertIn("Promise.all([request, minimumWait])", script)
        self.assertIn("window.location.assign(response.url || navigateUrl)", script)
        self.assertIn('"X-NamEngine-Progress": "1"', script)
        self.assertIn("syncOtherSelect", script)
        self.assertIn("select[data-other-select]", script)
        self.assertIn("input.required = isOther && select.required", script)
        self.assertIn("namengine:progress-step", script)
        self.assertIn("is-pulsing", script)
        self.assertIn("personalizeProgress(form)", script)
        self.assertIn("Building a shortlist for ${subject}", script)
        self.assertIn("Finding names for ${subject}", script)
        self.assertIn("HTMLFormElement.prototype.submit.call(form)", script)

    def test_progress_overlay_has_synced_node_animation_styles(self):
        css_path = os.path.join(self.app.static_folder, "css", "platform.css")
        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        self.assertIn(".progress-visual", css)
        self.assertIn(".progress-node-center", css)
        self.assertIn(".progress-visual-label", css)
        self.assertIn("@keyframes progress-node-pulse", css)
        self.assertIn(".progress-visual.is-pulsing .progress-node-center", css)
        self.assertIn("grid-template-columns: minmax(220px, 0.54fr) minmax(0, 1fr)", css)
        self.assertIn("width: min(218px, 68vw)", css)
        self.assertIn("max-height: calc(100vh - 28px)", css)
        self.assertIn("text-align: center", css)
        self.assertIn("background: #fff8ef", css)


if __name__ == "__main__":
    unittest.main()
