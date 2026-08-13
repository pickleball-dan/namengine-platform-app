import unittest

from app import create_app
from namengine.verticals import get_vertical


class PhaseThirtyEightGenerationUnavailableCopyTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def test_unavailable_page_does_not_show_internal_fallback_explanation(self):
        with self.app.test_request_context("/"):
            html = self.app.jinja_env.get_template("generation_unavailable.html").render(
                message="We’re having trouble generating this list right now. Please try again shortly.",
                vertical=get_vertical("baby"),
            )

        self.assertIn("We need a moment before trying again.", html)
        self.assertIn("Your answers are safe", html)
        self.assertNotIn("We’re having trouble generating this list right now. Please try again shortly.", html)
        self.assertIn("Go back and try again", html)
        self.assertNotIn("No fallback list was shown", html)
        self.assertNotIn("real engine", html)

    def test_business_unavailable_page_is_honest_about_quality_preserving_retry(self):
        with self.app.test_request_context("/"):
            html = self.app.jinja_env.get_template("generation_unavailable.html").render(
                message="We’re having trouble generating this list right now. Please try again shortly.",
                vertical=get_vertical("business"),
            )

        self.assertIn("Quality over filler", html)
        self.assertIn("We need a clean AI pass before showing business names.", html)
        self.assertIn("Rather than show generic fallback names as premium output", html)
        self.assertIn("Go back and try again", html)
        self.assertNotIn("We’re having trouble generating this list right now. Please try again shortly.", html)


if __name__ == "__main__":
    unittest.main()
