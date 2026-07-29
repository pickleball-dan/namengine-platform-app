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
        self.assertIn("checkout continuity cookie", text)
        self.assertIn("namengine_beta_return_*", text)
        self.assertIn("does not contain payment card information", text)
        self.assertIn("support@nam-engine.com", text)
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
        self.assertIn("checkout continuity cookie", text)
        self.assertIn("namengine_beta_return_*", text)
        self.assertIn("does not contain payment card information", text)
        self.assertIn("privacy@nam-engine.com", text)

    def test_footer_has_trust_links_and_pricing(self):
        response = self.app.get("/")
        text = response.get_data(as_text=True)

        self.assertIn('/#pricing', text)
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
        self.assertIn("What paid beta includes:", text)
        self.assertIn("beta-includes-list", text)
        self.assertIn("Try the first round", text)
        self.assertTrue("Request founding access" in text or "Try Baby Beta risk-free" in text)
        self.assertIn("100% refund", text)
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
        self.assertIn('/baby/beta/checkout', text)
        self.assertNotIn('href="https://buy.stripe.com/test_example"', text)
        self.assertIn("Try Baby Beta risk-free", text)
        self.assertIn("100% refund", text)

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
        self.assertNotIn("Try Baby Beta risk-free", text)
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
        self.assertIn("Try Baby Beta risk-free", text)
        self.assertIn("100% refund", text)
        self.assertIn("NamEngine suggestions are exploratory", text)
        self.assertIn("/disclaimers", text)


    def test_baby_paid_success_can_continue_with_paid_flag(self):
        response = self.app.get("/baby/beta?paid=1")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/baby?paid=1"', text)

    def test_baby_paid_success_can_return_to_existing_session(self):
        response = self.app.get("/baby/beta?paid=1&return_session=baby-testsession")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/results/session/baby-testsession?paid=1"', text)

    def test_beta_checkout_preserves_return_session_for_stripe_round_trip(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            checkout = self.app.get("/baby/beta/checkout?return_session=baby-testsession")
            paid_return = self.app.get("/baby/beta?paid=1")
            text = paid_return.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(checkout.status_code, 302)
        self.assertEqual(checkout.headers["Location"], "https://buy.stripe.com/test_example")
        self.assertIn("namengine_beta_return_baby=baby-testsession", checkout.headers["Set-Cookie"])
        self.assertEqual(paid_return.status_code, 200)
        self.assertIn('href="/results/session/baby-testsession?paid=1"', text)

    def test_free_baby_results_lock_refinement_behind_beta(self):
        response = self.app.get(
            "/baby/results",
            query_string={
                "gender": "Girl",
                "style": "Classic",
                "sound": "Soft",
            },
        )
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Try Baby Beta risk-free", text)
        self.assertIn("Your first list is free", text)
        self.assertIn("100% refund", text)
        self.assertNotIn('action="/refine"', text)

    def test_paid_baby_results_keep_refinement_form_unlocked(self):
        response = self.app.get(
            "/baby/results",
            query_string={
                "gender": "Girl",
                "style": "Classic",
                "sound": "Soft",
                "paid": "1",
            },
        )
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('action="/refine"', text)
        self.assertIn('name="paid" value="1"', text)
        self.assertNotIn("Try Baby Beta risk-free", text)

    def test_free_baby_refine_is_blocked_server_side(self):
        session_response = self.app.get(
            "/baby/results",
            query_string={
                "gender": "Girl",
                "style": "Classic",
                "sound": "Soft",
            },
        )
        session_text = session_response.get_data(as_text=True)
        marker = 'data-session-id="'
        start = session_text.index(marker) + len(marker)
        end = session_text.index('"', start)
        session_id = session_text[start:end]

        response = self.app.post("/refine", data={"session_id": session_id})
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 402)
        self.assertIn("Unlock the Baby founding beta", text)

    def test_pet_and_business_beta_pages_render_paid_offers(self):
        for route, label in (("/pet/beta", "Pet"), ("/business/beta", "Business")):
            with self.subTest(route=route):
                response = self.app.get(route)
                text = response.get_data(as_text=True)

                self.assertEqual(response.status_code, 200)
                self.assertIn(f"NamEngine {label}", text)
                self.assertIn(f"try {label} Beta risk-free", text)
                self.assertIn("100% refund", text)
                self.assertIn("Separate vertical access", text)

    def test_vertical_beta_uses_vertical_specific_payment_link_and_price(self):
        previous_link = os.environ.get("NAMENGINE_PET_BETA_PAYMENT_LINK")
        previous_price = os.environ.get("NAMENGINE_PET_BETA_PRICE")
        os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/pet_test"
        os.environ["NAMENGINE_PET_BETA_PRICE"] = "$7"
        try:
            response = self.app.get("/pet/beta")
            text = response.get_data(as_text=True)
        finally:
            if previous_link is None:
                os.environ.pop("NAMENGINE_PET_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = previous_link
            if previous_price is None:
                os.environ.pop("NAMENGINE_PET_BETA_PRICE", None)
            else:
                os.environ["NAMENGINE_PET_BETA_PRICE"] = previous_price

        self.assertEqual(response.status_code, 200)
        self.assertIn('/pet/beta/checkout', text)
        self.assertNotIn('href="https://buy.stripe.com/pet_test"', text)
        self.assertIn("$7", text)
        self.assertIn("Try Pet Beta risk-free", text)

    def test_free_business_results_lock_refinement_behind_vertical_beta(self):
        response = self.app.get(
            "/business/results",
            query_string={
                "industry": "Consulting",
                "style": "Modern",
                "audience": "Founders",
            },
        )
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Try Business Beta risk-free", text)
        self.assertIn("Your first list is free", text)
        self.assertIn("100% refund", text)
        self.assertIn('/business/beta?return_session=', text)
        self.assertNotIn('action="/refine"', text)


if __name__ == "__main__":
    unittest.main()
