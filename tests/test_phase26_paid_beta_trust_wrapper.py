import os
import unittest

from app import create_app


class PhaseTwentySixPaidBetaTrustWrapperTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app().test_client()

    def test_public_legal_pages_render(self):
        pages = {
            "/privacy": ("Privacy Policy", "Legal note"),
            "/terms": ("Terms of Use", "Legal note"),
            "/disclaimers": ("AI Disclosures &amp; Responsible Use", "Legal note"),
            "/data-protection": ("Data Protection &amp; Privacy Policy", "Legal note"),
        }
        for path, (expected, notice_label) in pages.items():
            with self.subTest(path=path):
                response = self.app.get(path)
                self.assertEqual(response.status_code, 200)
                text = response.get_data(as_text=True)
                self.assertIn(expected, text)
                self.assertIn(notice_label, text)

    def test_privacy_policy_has_production_disclosures(self):
        response = self.app.get("/privacy")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Effective Date:", text)
        self.assertIn("July 20, 2026", text)
        self.assertIn("trusted AI service providers", text)
        self.assertIn("NamEngine does not sell personal information", text)
        self.assertIn("privacy@namengine.com", text)
        self.assertNotIn("replace with your preferred contact email", text)

    def test_terms_policy_has_production_disclosures(self):
        response = self.app.get("/terms")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Effective Date:", text)
        self.assertIn("July 20, 2026", text)
        self.assertIn("NamEngine LLC", text)
        self.assertIn("artificial intelligence services", text)
        self.assertIn("THE SERVICES ARE PROVIDED", text)
        self.assertIn("support@nam-engine.com", text)
        self.assertNotIn("replace if different", text)

    def test_ai_disclosures_have_responsible_use_copy(self):
        response = self.app.get("/disclaimers")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("AI Disclosures &amp; Responsible Use", text)
        self.assertIn("Effective Date:", text)
        self.assertIn("July 20, 2026", text)
        self.assertIn("AI is intended to assist your decision-making", text)
        self.assertIn("NamEngine does not reserve names for individual users", text)
        self.assertIn("support@nam-engine.com", text)

    def test_data_protection_has_production_privacy_copy(self):
        response = self.app.get("/data-protection")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Data Protection &amp; Privacy Policy", text)
        self.assertIn("Effective Date:", text)
        self.assertIn("July 20, 2026", text)
        self.assertIn("We never sell your personal information", text)
        self.assertIn("trusted artificial intelligence technology providers", text)
        self.assertIn("privacy@nam-engine.com", text)

    def test_footer_has_trust_links(self):
        response = self.app.get("/")
        text = response.get_data(as_text=True)

        self.assertNotIn('/baby/beta', text)
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
        self.assertIn("What paid beta includes:", text)
        self.assertIn("beta-includes-list", text)
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
        self.assertIn("You have unlocked deeper taste discovery", text)
        self.assertIn("Start Baby name discovery", text)
        self.assertNotIn("Start with a free first round", text)
        self.assertNotIn("Join paid beta", text)
        self.assertNotIn("https://buy.stripe.com/test_example", text)

    def test_baby_intake_surfaces_paid_beta_and_trust_copy(self):
        response = self.app.get("/baby")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("See paid beta", text)
        self.assertIn("Thoughtful AI guidance", text)
        self.assertIn("Your family’s story stays private", text)
        self.assertIn("You’re always in control", text)

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
