import os
import unittest
from unittest.mock import patch

import app as namengine_app
from app import create_app, _beta_access_secret, _stripe_checkout_session_paid, make_session_id
from namengine.core import get_session_snapshot
from namengine.verticals import get_vertical


class PhaseTwentySixPaidBetaTrustWrapperTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app().test_client()

    def test_access_secret_does_not_fall_back_to_public_constant(self):
        previous_access = os.environ.pop("NAMENGINE_ACCESS_TOKEN_SECRET", None)
        previous_telemetry = os.environ.pop("NAMENGINE_TELEMETRY_TOKEN", None)
        try:
            self.assertNotEqual(_beta_access_secret(), "namengine-local-access-token")
        finally:
            if previous_access is not None:
                os.environ["NAMENGINE_ACCESS_TOKEN_SECRET"] = previous_access
            if previous_telemetry is not None:
                os.environ["NAMENGINE_TELEMETRY_TOKEN"] = previous_telemetry

    def test_stripe_checkout_verification_fails_closed_without_matching_payment_link(self):
        previous_secret = os.environ.get("STRIPE_SECRET_KEY")
        previous_link = os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
        previous_link_id = os.environ.pop("NAMENGINE_BABY_STRIPE_PAYMENT_LINK_ID", None)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        try:
            with patch.object(
                namengine_app,
                "_stripe_api_get",
                return_value={
                    "payment_status": "paid",
                    "status": "complete",
                    "payment_link": "plink_other",
                },
            ):
                self.assertFalse(_stripe_checkout_session_paid("cs_test_paid", get_vertical("baby")))
        finally:
            if previous_secret is None:
                os.environ.pop("STRIPE_SECRET_KEY", None)
            else:
                os.environ["STRIPE_SECRET_KEY"] = previous_secret
            if previous_link is not None:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous_link
            if previous_link_id is not None:
                os.environ["NAMENGINE_BABY_STRIPE_PAYMENT_LINK_ID"] = previous_link_id

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
        self.assertIn("namengine_access_return_*", text)
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
        self.assertIn("namengine_access_return_*", text)
        self.assertIn("does not contain payment card information", text)
        self.assertIn("privacy@nam-engine.com", text)

    def test_footer_has_trust_links_and_pricing(self):
        response = self.app.get("/")
        text = response.get_data(as_text=True)

        self.assertIn('/#pricing', text)
        self.assertNotIn('/baby/access', text)
        self.assertIn('/privacy', text)
        self.assertIn('/terms', text)
        self.assertIn('/disclaimers', text)
        self.assertIn('/data-protection', text)

    def test_baby_beta_page_renders_paid_offer(self):
        response = self.app.get("/baby/access")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("NamEngine Baby", text)
        self.assertIn("NamEngine Access", text)
        self.assertIn("What paid access includes:", text)
        self.assertIn("beta-includes-list", text)
        self.assertIn("Refined rounds shaped by your Love and No reactions", text)
        self.assertNotIn("Save, compare, and share favorite-name tools", text)
        self.assertIn("$9.99", text)
        self.assertNotIn("$19", text)
        self.assertNotIn("Try the first round", text)
        self.assertIn("100% money-back guarantee", text)
        self.assertNotIn("NAMENGINE_BABY_BETA_PAYMENT_LINK", text)

    def test_baby_beta_uses_payment_link_when_configured(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            response = self.app.get("/baby/access")
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(response.status_code, 200)
        self.assertIn('/baby/access/checkout', text)
        self.assertNotIn('href="https://buy.stripe.com/test_example"', text)
        self.assertIn("Unlock Baby Access", text)
        self.assertIn("100% money-back guarantee", text)

    def test_beta_checkout_uses_current_vertical_stripe_payment_links(self):
        previous = {
            key: os.environ.pop(key, None)
            for key in (
                "NAMENGINE_BUSINESS_BETA_PAYMENT_LINK",
                "NAMENGINE_PET_BETA_PAYMENT_LINK",
                "NAMENGINE_BABY_BETA_PAYMENT_LINK",
            )
        }
        try:
            expected_locations = {
                "/business/access/checkout": "https://buy.stripe.com/test_aFa3cvchXg1E5CS2Yqds401",
                "/pet/access/checkout": "https://buy.stripe.com/test_6oU5kD0zf4iW8P41Umds402",
                "/baby/access/checkout": "https://buy.stripe.com/test_4gM5kDchX5n0aXc9mOds403",
            }
            for path, expected in expected_locations.items():
                with self.subTest(path=path):
                    checkout = self.app.get(path)
                    self.assertEqual(checkout.status_code, 302)
                    self.assertEqual(checkout.headers["Location"], expected)
        finally:
            for key, value in previous.items():
                if value is not None:
                    os.environ[key] = value

    def test_legacy_baby_stripe_payment_link_remaps_to_current_vertical_link(self):
        keys = {
            "business": "NAMENGINE_BUSINESS_BETA_PAYMENT_LINK",
            "pet": "NAMENGINE_PET_BETA_PAYMENT_LINK",
            "baby": "NAMENGINE_BABY_BETA_PAYMENT_LINK",
        }
        expected_locations = {
            "business": "https://buy.stripe.com/test_aFa3cvchXg1E5CS2Yqds401",
            "pet": "https://buy.stripe.com/test_6oU5kD0zf4iW8P41Umds402",
            "baby": "https://buy.stripe.com/test_4gM5kDchX5n0aXc9mOds403",
        }
        previous = {key: os.environ.get(key) for key in keys.values()}
        try:
            for key in keys.values():
                os.environ[key] = "https://buy.stripe.com/test_bJe5kDfu99Dg1mCdD4ds400"
            for slug, expected in expected_locations.items():
                with self.subTest(slug=slug):
                    checkout = self.app.get(f"/{slug}/access/checkout")
                    self.assertEqual(checkout.status_code, 302)
                    self.assertEqual(checkout.headers["Location"], expected)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_returning_results_access_page_removes_first_round_prompt(self):
        previous = os.environ.get("NAMENGINE_PET_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/pet_test"
        try:
            response = self.app.get("/pet/access?return_session=pet-testsession")
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_PET_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Try the first round", text)
        self.assertNotIn("Try first round", text)
        self.assertNotIn("Start with a free first round", text)
        self.assertIn("return to this report", text)
        self.assertNotIn("Generate your first preview list", text)
        self.assertNotIn("Naming Experiences", text)
        self.assertIn("Unlock Pet Access", text)
        self.assertIn('/pet/access/checkout?return_session=pet-testsession', text)

    def test_cross_vertical_return_session_is_ignored_on_access_page(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/baby_test"
        try:
            response = self.app.get("/baby/access?return_session=pet-testsession")
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("pet-testsession", text)
        self.assertNotIn("shaped by your first reactions", text)
        self.assertIn("Generate your first preview list", text)
        self.assertIn('/baby/access/checkout', text)

    def test_naked_paid_query_does_not_unlock_access_page(self):
        response = self.app.get("/baby/access?paid=1")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Payment received", text)
        self.assertIn("Generate your first preview list", text)
        self.assertIn("$9.99", text)
        self.assertNotIn("$19", text)
        self.assertNotIn("Try the first round", text)

    def test_checkout_start_plus_manual_paid_query_does_not_unlock_access_page(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            checkout = self.app.get("/baby/access/checkout")
            response = self.app.get("/baby/access?paid=1")
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(checkout.status_code, 302)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Payment received", text)
        self.assertIn("Generate your first preview list", text)
        self.assertIn("Unlock Baby Access", text)

    def test_baby_beta_paid_success_state_requires_verified_checkout(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            checkout = self.app.get("/baby/access/checkout")
            with patch("app._stripe_checkout_session_paid", return_value=True):
                response = self.app.get("/baby/access?checkout_session_id=cs_test_paid")
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(checkout.status_code, 302)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Payment received", text)
        self.assertIn("You have unlocked deeper taste discovery", text)
        self.assertIn("Start Baby name discovery", text)
        self.assertNotIn("Start with a free first round", text)
        self.assertNotIn("Unlock Baby Access", text)
        self.assertNotIn("https://buy.stripe.com/test_example", text)

    def test_paid_return_session_success_page_points_back_to_full_report(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            self.app.get("/baby/access/checkout?return_session=baby-testsession")
            with patch("app._stripe_checkout_session_paid", return_value=True):
                response = self.app.get("/baby/access?checkout_session_id=cs_test_paid&return_session=baby-testsession")
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/results/session/baby-testsession")
        self.assertNotIn("Start Baby name discovery", text)

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
        self.assertIn("Unlock Baby Access", text)
        self.assertIn("100% money-back guarantee", text)
        self.assertIn("NamEngine suggestions are exploratory", text)
        self.assertIn("/disclaimers", text)


    def test_baby_paid_success_continue_link_goes_to_free_first_round_without_paid_query(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            self.app.get("/baby/access/checkout")
            with patch("app._stripe_checkout_session_paid", return_value=True):
                response = self.app.get("/baby/access?checkout_session_id=cs_test_paid")
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/baby"', text)
        self.assertNotIn("?paid=1", text)

    def test_baby_paid_success_redirects_to_existing_session_without_paid_query(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            self.app.get("/baby/access/checkout?return_session=baby-testsession")
            with patch("app._stripe_checkout_session_paid", return_value=True):
                response = self.app.get("/baby/access?checkout_session_id=cs_test_paid")
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/results/session/baby-testsession")
        self.assertNotIn("?paid=1", response.headers["Location"])

    def test_beta_checkout_preserves_return_session_for_stripe_round_trip(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            checkout = self.app.get("/baby/access/checkout?return_session=baby-testsession")
            with patch("app._stripe_checkout_session_paid", return_value=True):
                paid_return = self.app.get("/baby/access?checkout_session_id=cs_test_paid")
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        checkout_cookies = "\n".join(checkout.headers.getlist("Set-Cookie"))
        self.assertEqual(checkout.status_code, 302)
        self.assertEqual(checkout.headers["Location"], "https://buy.stripe.com/test_example")
        self.assertIn("namengine_access_checkout_baby=", checkout_cookies)
        self.assertIn("namengine_access_return_baby=baby-testsession", checkout_cookies)
        self.assertEqual(paid_return.status_code, 302)
        self.assertEqual(paid_return.headers["Location"], "/results/session/baby-testsession")
        self.assertNotIn("?paid=1", paid_return.headers["Location"])

    def test_beta_checkout_creates_stripe_session_with_return_session_success_url(self):
        previous_secret = os.environ.get("STRIPE_SECRET_KEY")
        previous_link = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        previous_link_id = os.environ.get("NAMENGINE_BABY_STRIPE_PAYMENT_LINK_ID")
        previous_price_id = os.environ.get("NAMENGINE_BABY_STRIPE_PRICE_ID")
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        os.environ["NAMENGINE_BABY_STRIPE_PAYMENT_LINK_ID"] = "plink_baby"
        os.environ["NAMENGINE_BABY_STRIPE_PRICE_ID"] = "price_baby"
        posted = {}
        try:
            def fake_post(path, secret_key, data):
                posted["path"] = path
                posted["secret_key"] = secret_key
                posted["data"] = data
                return {"url": "https://checkout.stripe.com/c/session_test"}

            with patch.object(namengine_app, "_stripe_api_post", side_effect=fake_post):
                checkout = self.app.get(
                    "/baby/access/checkout?return_session=baby-testsession",
                    base_url="https://nam-engine.com",
                )
        finally:
            for key, value in {
                "STRIPE_SECRET_KEY": previous_secret,
                "NAMENGINE_BABY_BETA_PAYMENT_LINK": previous_link,
                "NAMENGINE_BABY_STRIPE_PAYMENT_LINK_ID": previous_link_id,
                "NAMENGINE_BABY_STRIPE_PRICE_ID": previous_price_id,
            }.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(checkout.status_code, 302)
        self.assertEqual(checkout.headers["Location"], "https://checkout.stripe.com/c/session_test")
        self.assertEqual(posted["path"], "checkout/sessions")
        self.assertEqual(posted["secret_key"], "sk_test_example")
        self.assertEqual(posted["data"]["line_items[0][price]"], "price_baby")
        self.assertEqual(
            posted["data"]["success_url"],
            "https://nam-engine.com/baby/access?checkout_session_id={CHECKOUT_SESSION_ID}&return_session=baby-testsession",
        )
        self.assertEqual(
            posted["data"]["cancel_url"],
            "https://nam-engine.com/baby/access?return_session=baby-testsession",
        )
        self.assertEqual(posted["data"]["metadata[namengine_vertical]"], "baby")
        self.assertEqual(posted["data"]["metadata[namengine_return_session]"], "baby-testsession")
        checkout_cookies = "\n".join(checkout.headers.getlist("Set-Cookie"))
        self.assertIn("namengine_access_checkout_baby=", checkout_cookies)
        self.assertIn("namengine_access_return_baby=baby-testsession", checkout_cookies)

    def test_stripe_checkout_verification_accepts_app_created_session_metadata(self):
        previous_secret = os.environ.get("STRIPE_SECRET_KEY")
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        try:
            with patch.object(
                namengine_app,
                "_stripe_api_get",
                return_value={
                    "payment_status": "paid",
                    "status": "complete",
                    "payment_link": None,
                    "metadata": {
                        "namengine_access": "1",
                        "namengine_vertical": "baby",
                    },
                },
            ):
                self.assertTrue(_stripe_checkout_session_paid("cs_test_paid", get_vertical("baby")))
        finally:
            if previous_secret is None:
                os.environ.pop("STRIPE_SECRET_KEY", None)
            else:
                os.environ["STRIPE_SECRET_KEY"] = previous_secret

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
        self.assertIn("Unlock Baby Access", text)
        self.assertIn("Your first list is free", text)
        self.assertIn("100% money-back guarantee", text)
        self.assertNotIn('action="/refine"', text)

    def test_naked_paid_baby_results_still_lock_refinement(self):
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
        self.assertIn("Unlock Baby Access", text)
        self.assertNotIn('action="/refine"', text)
        self.assertNotIn('name="paid" value="1"', text)

    def test_checkout_cookie_unlocks_baby_results_without_paid_query_in_form(self):
        previous = os.environ.get("NAMENGINE_BABY_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            self.app.get("/baby/access/checkout")
            with patch("app._stripe_checkout_session_paid", return_value=True):
                self.app.get("/baby/access?checkout_session_id=cs_test_paid")
            response = self.app.get(
                "/baby/results",
                query_string={
                    "gender": "Girl",
                    "style": "Classic",
                    "sound": "Soft",
                },
            )
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_BABY_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_BABY_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(response.status_code, 200)
        self.assertIn('action="/refine"', text)
        self.assertNotIn('name="paid" value="1"', text)
        self.assertNotIn("Unlock Baby Access", text)

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
        self.assertIn("Unlock Baby access", text)

    def test_free_post_results_actions_redirect_to_access(self):
        query = b"gender=Girl&style=Classic&sound=Soft"
        session_id = make_session_id("baby", query)
        self.app.get(f"/baby/results?{query.decode('utf-8')}")
        result_id = namengine_app.json_loads(get_session_snapshot(session_id)["results"][0]["result_json"])["id"]

        routes = (
            ("detail", self.app.get(f"/baby/name/{session_id}/{result_id}")),
            ("compare", self.app.get(f"/compare/{session_id}")),
            ("share", self.app.get(f"/share/{session_id}")),
            (
                "choose",
                self.app.post(
                    "/choose",
                    data={"session_id": session_id, "result_id": result_id},
                    follow_redirects=False,
                ),
            ),
        )

        for label, response in routes:
            with self.subTest(label=label):
                self.assertEqual(response.status_code, 302)
                self.assertIn(f"/baby/access?return_session={session_id}", response.headers["Location"])

    def test_pending_checkout_cookie_alone_does_not_unlock_back_button_refine(self):
        previous = os.environ.get("NAMENGINE_PET_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/pet_test"
        try:
            session_response = self.app.get(
                "/pet/results",
                query_string={
                    "pet_type": "Dog",
                    "style": "Friendly",
                    "personality": "Playful",
                },
            )
            session_text = session_response.get_data(as_text=True)
            marker = 'data-session-id="'
            start = session_text.index(marker) + len(marker)
            end = session_text.index('"', start)
            session_id = session_text[start:end]
            self.app.get(f"/pet/access/checkout?return_session={session_id}")
            response = self.app.post("/refine", data={"session_id": session_id, "instruction": "warmer"})
            text = response.get_data(as_text=True)
        finally:
            if previous is None:
                os.environ.pop("NAMENGINE_PET_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = previous

        self.assertEqual(response.status_code, 402)
        self.assertIn("Unlock Pet access", text)
        self.assertNotIn('action="/refine"', text)

    def test_pet_and_business_beta_pages_render_paid_offers(self):
        for route, label in (("/pet/access", "Pet"), ("/business/access", "Business")):
            with self.subTest(route=route):
                response = self.app.get(route)
                text = response.get_data(as_text=True)

                self.assertEqual(response.status_code, 200)
                self.assertIn(f"NamEngine {label}", text)
                self.assertIn("NamEngine Access", text)
                self.assertIn("What paid access includes:", text)
                self.assertIn("Refined rounds shaped by your Love and No reactions", text)
                self.assertNotIn("Save, compare, and share favorite-name tools", text)
                self.assertIn("$9.99", text)
                self.assertNotIn("$19", text)
                self.assertNotIn("Try the first round", text)
                self.assertIn("100% money-back guarantee", text)
                self.assertNotIn("Separate vertical access", text)

    def test_vertical_beta_uses_vertical_specific_payment_link_and_stripe_price_source(self):
        previous_link = os.environ.get("NAMENGINE_PET_BETA_PAYMENT_LINK")
        previous_env_price = os.environ.get("NAMENGINE_PET_BETA_PRICE")
        os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/pet_test"
        os.environ["NAMENGINE_PET_BETA_PRICE"] = "$7"
        try:
            response = self.app.get("/pet/access")
            text = response.get_data(as_text=True)
        finally:
            if previous_link is None:
                os.environ.pop("NAMENGINE_PET_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = previous_link
            if previous_env_price is None:
                os.environ.pop("NAMENGINE_PET_BETA_PRICE", None)
            else:
                os.environ["NAMENGINE_PET_BETA_PRICE"] = previous_env_price

        self.assertEqual(response.status_code, 200)
        self.assertIn('/pet/access/checkout', text)
        self.assertNotIn('href="https://buy.stripe.com/pet_test"', text)
        self.assertNotIn("$7", text)
        self.assertIn("$9.99", text)
        self.assertIn("Unlock Pet Access", text)

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
        self.assertIn("Unlock Business Access", text)
        self.assertIn("Your first list is free", text)
        self.assertIn("100% money-back guarantee", text)
        self.assertIn('/business/access?return_session=', text)
        self.assertNotIn('action="/refine"', text)


if __name__ == "__main__":
    unittest.main()
