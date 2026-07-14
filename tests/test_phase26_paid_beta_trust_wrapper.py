import os
import unittest

from app import create_app


class PhaseTwentySixPaidBetaTrustWrapperTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app().test_client()

    def test_public_legal_pages_render(self):
        pages = {
            "/privacy": "Privacy Policy",
            "/terms": "Terms of Use",
            "/disclaimers": "Disclaimers",
            "/data-protection": "Data Protection",
        }
        for path, expected in pages.items():
            with self.subTest(path=path):
                response = self.app.get(path)
                self.assertEqual(response.status_code, 200)
                text = response.get_data(as_text=True)
                self.assertIn(expected, text)
                self.assertIn("Beta notice", text)

    def test_footer_has_trust_links(self):
        response = self.app.get("/")
        text = response.get_data(as_text=True)

        self.assertIn('/baby/beta', text)
        self.assertIn('/privacy', text)
        self.assertIn('/terms', text)
        self.assertIn('/disclaimers', text)
        self.assertIn('/data-protection', text)

    def test_baby_beta_page_renders_paid_offer(self):
        response = self.app.get("/baby/beta")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("NamEngine Baby", text)
        self.assertIn("Founding beta", text)
        self.assertIn("Try the first round", text)
        self.assertTrue("Request founding access" in text or "Join paid beta" in text)
        self.assertNotIn("NAMENGINE_BABY_BETA_PAYMENT_LINK", text)

    def test_baby_beta_uses_payment_link_when_configured(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            response = self.app.get("/baby/beta")
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(response.status_code, 200)
        self.assertIn("https://buy.stripe.com/test_example", text)
        self.assertIn("Join paid beta", text)

    def test_baby_beta_paid_success_state(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            response = self.app.get("/baby/beta?paid=1")
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(response.status_code, 200)
        self.assertIn("Payment received", text)
        self.assertIn("Start Baby name discovery", text)
        self.assertNotIn("Join paid beta", text)
        self.assertNotIn("https://buy.stripe.com/test_example", text)

    def test_baby_intake_surfaces_paid_beta_and_trust_copy(self):
        response = self.app.get("/baby")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("See paid beta", text)
        self.assertIn("AI-assisted", text)
        self.assertIn("Do not enter sensitive personal data", text)
        self.assertIn("Your judgment", text)

    def test_baby_results_include_disclaimer_and_paid_depth_cta(self):
        response = self.app.get(
            "/baby/results",
            query_string={
                "gender": "Girl",
                "style": "Classic",
                "notes": "Warm and timeless",
            },
        )
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Unlock paid beta depth", text)
        self.assertIn("NamEngine suggestions are exploratory", text)
        self.assertIn("/disclaimers", text)


if __name__ == "__main__":
    unittest.main()
