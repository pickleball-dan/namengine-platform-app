import unittest
from pathlib import Path

from app import create_app


class BabyCheckInV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.testing = True
        cls.client = cls.app.test_client()
        cls.root = Path(cls.app.root_path)
        cls.js = (cls.root / "static" / "js" / "baby-intake-polish.js").read_text(encoding="utf-8")

    def test_checkin_uses_generic_unsubmitted_markup(self):
        body = self.client.get("/baby").get_data(as_text=True)

        self.assertEqual(body.count("data-intake-checkin"), 1)
        self.assertIn("data-checkin-heading", body)
        self.assertIn("data-checkin-options", body)
        self.assertNotIn('name="checkin', body)
        self.assertNotIn('name="midpoint', body)

    def test_configuration_inserts_after_sound_before_cultural_context(self):
        self.assertIn('insertAfter: "sound"', self.js)
        self.assertIn('heading: "Are we asking the right questions?"', self.js)
        self.assertIn(
            'supportingCopy: "We want to understand what matters most to you before suggesting names."',
            self.js,
        )
        self.assertLess(self.js.index('"sound", "cultural_context"'), self.js.index("intakeStepConfigurations"))
        self.assertIn("const following = checkInFollowingQuestion()", self.js)

    def test_checkin_has_all_stable_response_keys_and_advances_immediately(self):
        for key, label in (
            ("yes", "Yes, these questions make sense"),
            ("mostly", "Mostly"),
            ("unsure", "I’m not sure yet"),
        ):
            self.assertIn(f'{{ key: "{key}", label: "{label}" }}', self.js)
        self.assertIn("selectCheckInResponse(checkInChoice)", self.js)
        self.assertIn("if (following) showQuestion(following)", self.js)

    def test_checkin_does_not_enter_question_or_progress_collections(self):
        self.assertIn('form.querySelectorAll("[data-baby-question]")', self.js)
        self.assertNotIn("questions.push(checkIn", self.js)
        self.assertIn("progressCopy.hidden = true", self.js)
        self.assertIn("updateJourney(anchor)", self.js)
        self.assertNotIn("updateProgress(anchor)", self.js)

    def test_checkin_back_and_restore_paths_are_stable(self):
        self.assertIn(
            "checkInReturn.hidden = !(checkInResponse && question === checkInFollowingQuestion())",
            self.js,
        )
        self.assertIn("if (anchor) showQuestion(anchor)", self.js)
        self.assertIn("showCheckIn()", self.js)
        self.assertIn('choice.setAttribute("aria-checked", String(selected))', self.js)

    def test_session_storage_persists_only_the_internal_response(self):
        self.assertIn('storageKey: "namengine:intake-checkin:baby:midpoint:v1"', self.js)
        self.assertIn("window.sessionStorage.getItem(checkInConfiguration.storageKey)", self.js)
        self.assertIn("window.sessionStorage.setItem(checkInConfiguration.storageKey, JSON.stringify({ response }))", self.js)
        self.assertNotIn("localStorage.setItem(checkInConfiguration.storageKey", self.js)

    def test_existing_skip_and_feelings_route_contracts_remain(self):
        body = self.client.get("/baby").get_data(as_text=True)

        self.assertIn('action="/baby/feelings"', body)
        self.assertIn('class="baby-skip" data-baby-skip>Skip for now</button>', body)
        self.assertIn('confirmAndAdvance(question, "Skipped for now")', self.js)
        self.assertIn("HTMLFormElement.prototype.submit.call(form)", self.js)

    def test_checkin_is_excluded_from_visible_answer_history(self):
        render_history = self.js.split("function renderHistory(question)", 1)[1].split(
            "function escapeHtml", 1
        )[0]

        self.assertIn("answeredBefore(question)", render_history)
        self.assertNotIn("checkInResponse", render_history)


if __name__ == "__main__":
    unittest.main()
