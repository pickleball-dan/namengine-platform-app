import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app import create_app, make_session_id
from namengine.core.storage import get_beta_usage, get_session_snapshot
from namengine.verticals import get_vertical


class BetaUsageLimitsTest(unittest.TestCase):
    def setUp(self):
        self._previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self._previous_free_hours = os.environ.get("NAMENGINE_BETA_FREE_ACCESS_HOURS")
        self._tmp = tempfile.mkdtemp()
        os.environ["NAMENGINE_DB_PATH"] = os.path.join(self._tmp, "beta-usage.sqlite3")
        os.environ["NAMENGINE_BETA_FREE_ACCESS_HOURS"] = "24"
        self.client = create_app().test_client()

    def tearDown(self):
        self.client = None
        if self._previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self._previous_db_path
        if self._previous_free_hours is None:
            os.environ.pop("NAMENGINE_BETA_FREE_ACCESS_HOURS", None)
        else:
            os.environ["NAMENGINE_BETA_FREE_ACCESS_HOURS"] = self._previous_free_hours
        try:
            Path(os.path.join(self._tmp, "beta-usage.sqlite3")).unlink(missing_ok=True)
            Path(self._tmp).rmdir()
        except PermissionError:
            pass

    def _baby_first_query(self) -> str:
        return "gender=Girl&style=Classic&sound=Soft"

    def _first_query_for(self, vertical: str) -> str:
        return {
            "baby": self._baby_first_query(),
            "pet": "pet_type=Dog&style=Classic&vibe=Playful",
            "business": "business_description=Design+studio&audience=Premium+clients&style=Premium+and+refined",
        }[vertical]

    def _extract_session_id(self, html: str) -> str:
        marker = 'data-session-id="'
        start = html.index(marker) + len(marker)
        end = html.index('"', start)
        return html[start:end]

    def _visitor_cookie_value(self) -> str:
        cookie = self.client.get_cookie("namengine_beta_visitor_id")
        self.assertIsNotNone(cookie)
        return cookie.value

    def _expire_usage(self, visitor_id: str, vertical: str = "baby") -> None:
        expired = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        with sqlite3.connect(os.environ["NAMENGINE_DB_PATH"]) as connection:
            connection.execute(
                """
                UPDATE beta_usage
                SET free_access_expires_at = ?
                WHERE visitor_id = ? AND vertical = ?
                """,
                (expired, visitor_id, vertical),
            )
            connection.commit()

    def test_first_free_list_creates_server_side_usage_ledger(self):
        response = self.client.get(f"/baby/results?{self._baby_first_query()}")
        text = response.get_data(as_text=True)
        session_id = self._extract_session_id(text)
        visitor_id = self._visitor_cookie_value()

        usage = get_beta_usage(visitor_id, "baby")

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(get_session_snapshot(session_id))
        self.assertIsNotNone(usage)
        self.assertEqual(usage["free_session_id"], session_id)
        self.assertEqual(usage["free_generation_count"], 1)
        self.assertTrue(usage["free_access_expires_at"])

    def test_same_free_list_is_viewable_before_expiry_but_blocked_after_expiry(self):
        first = self.client.get(f"/baby/results?{self._baby_first_query()}")
        session_id = self._extract_session_id(first.get_data(as_text=True))
        visitor_id = self._visitor_cookie_value()

        before_expiry = self.client.get(f"/results/session/{session_id}", follow_redirects=False)
        self._expire_usage(visitor_id)
        after_expiry = self.client.get(f"/results/session/{session_id}", follow_redirects=False)

        self.assertEqual(before_expiry.status_code, 200)
        self.assertEqual(after_expiry.status_code, 302)
        self.assertIn(f"/baby/access?return_session={session_id}", after_expiry.headers["Location"])

    def test_expired_free_browser_cannot_generate_another_list(self):
        self.client.get(f"/baby/results?{self._baby_first_query()}")
        visitor_id = self._visitor_cookie_value()
        self._expire_usage(visitor_id)

        second_query = "gender=Boy&style=Modern&sound=Bold"
        second_session_id = make_session_id("baby", second_query.encode("utf-8"))
        second = self.client.get(f"/baby/results?{second_query}", follow_redirects=False)

        self.assertEqual(second.status_code, 302)
        self.assertIn(f"/baby/access?return_session={second_session_id}", second.headers["Location"])
        self.assertIsNone(get_session_snapshot(second_session_id))

    def test_paid_unlock_bypasses_expired_free_usage(self):
        first = self.client.get(f"/baby/results?{self._baby_first_query()}")
        session_id = self._extract_session_id(first.get_data(as_text=True))
        visitor_id = self._visitor_cookie_value()
        self._expire_usage(visitor_id)

        # Simulate a valid local paid-access cookie without going through Stripe.
        from app import _signed_beta_access_token, beta_unlock_cookie_name
        from namengine.verticals import get_vertical
        vertical = get_vertical("baby")
        self.client.set_cookie(beta_unlock_cookie_name(vertical), _signed_beta_access_token(vertical))

        response = self.client.get(f"/results/session/{session_id}", follow_redirects=False)

        self.assertEqual(response.status_code, 200)

    def test_access_checkout_link_carries_first_generated_list_from_usage_ledger(self):
        first = self.client.get(f"/pet/results?{self._first_query_for('pet')}")
        session_id = self._extract_session_id(first.get_data(as_text=True))
        previous_link = os.environ.get("NAMENGINE_PET_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            access = self.client.get("/pet/access")
            checkout = self.client.get("/pet/access/checkout", follow_redirects=False)
        finally:
            if previous_link is None:
                os.environ.pop("NAMENGINE_PET_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = previous_link

        self.assertIn(f"/pet/access/checkout?return_session={session_id}", access.get_data(as_text=True))
        checkout_cookies = "\n".join(checkout.headers.getlist("Set-Cookie"))
        self.assertIn(f"namengine_access_return_pet={session_id}", checkout_cookies)

    def test_paid_checkout_return_resumes_existing_generated_list_without_return_session(self):
        for vertical in ("baby", "pet", "business"):
            with self.subTest(vertical=vertical):
                self.client = create_app().test_client()
                first = self.client.get(f"/{vertical}/results?{self._first_query_for(vertical)}")
                session_id = self._extract_session_id(first.get_data(as_text=True))
                env_key = f"NAMENGINE_{vertical.upper()}_BETA_PAYMENT_LINK"
                previous = os.environ.get(env_key)
                os.environ[env_key] = "https://buy.stripe.com/test_example"
                try:
                    checkout = self.client.get(f"/{vertical}/access/checkout", follow_redirects=False)
                    with patch("app._stripe_checkout_session_paid", return_value=True):
                        paid_return = self.client.get(
                            f"/{vertical}/access?checkout_session_id=cs_test_paid",
                            follow_redirects=False,
                        )
                    paid_access_revisit = self.client.get(f"/{vertical}/access", follow_redirects=False)
                finally:
                    if previous is None:
                        os.environ.pop(env_key, None)
                    else:
                        os.environ[env_key] = previous

                self.assertEqual(checkout.status_code, 302)
                self.assertEqual(paid_return.status_code, 302)
                self.assertEqual(paid_return.headers["Location"], f"/results/session/{session_id}")
                self.assertEqual(paid_access_revisit.status_code, 302)
                self.assertEqual(paid_access_revisit.headers["Location"], f"/results/session/{session_id}")

    def test_paid_checkout_return_recovers_prior_list_from_signed_checkout_cookie(self):
        from app import _signed_beta_access_token, beta_pending_cookie_name

        first = self.client.get(f"/pet/results?{self._first_query_for('pet')}")
        session_id = self._extract_session_id(first.get_data(as_text=True))
        vertical = get_vertical("pet")
        returning_client = create_app().test_client()
        returning_client.set_cookie(
            beta_pending_cookie_name(vertical),
            _signed_beta_access_token(vertical, session_id),
        )

        with patch("app._stripe_checkout_session_paid", return_value=True):
            paid_return = returning_client.get(
                "/pet/access?checkout_session_id=cs_test_paid",
                follow_redirects=False,
            )

        self.assertEqual(paid_return.status_code, 302)
        self.assertEqual(paid_return.headers["Location"], f"/results/session/{session_id}")

    def test_payment_link_fallback_carries_prior_list_client_reference_id(self):
        first = self.client.get(f"/pet/results?{self._first_query_for('pet')}")
        session_id = self._extract_session_id(first.get_data(as_text=True))
        previous_link = os.environ.get("NAMENGINE_PET_BETA_PAYMENT_LINK")
        os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = "https://buy.stripe.com/test_example"
        try:
            with patch("app._create_stripe_checkout_session", return_value=""):
                checkout = self.client.get("/pet/access/checkout", follow_redirects=False)
        finally:
            if previous_link is None:
                os.environ.pop("NAMENGINE_PET_BETA_PAYMENT_LINK", None)
            else:
                os.environ["NAMENGINE_PET_BETA_PAYMENT_LINK"] = previous_link

        self.assertEqual(checkout.status_code, 302)
        self.assertEqual(
            checkout.headers["Location"],
            f"https://buy.stripe.com/test_example?client_reference_id={session_id}",
        )

    def test_paid_checkout_return_recovers_payment_link_client_reference_id(self):
        from app import _signed_beta_access_token, beta_pending_cookie_name

        first = self.client.get(f"/pet/results?{self._first_query_for('pet')}")
        session_id = self._extract_session_id(first.get_data(as_text=True))
        vertical = get_vertical("pet")
        returning_client = create_app().test_client()
        returning_client.set_cookie(
            beta_pending_cookie_name(vertical),
            _signed_beta_access_token(vertical),
        )
        previous_secret = os.environ.get("STRIPE_SECRET_KEY")
        previous_link_id = os.environ.get("NAMENGINE_PET_STRIPE_PAYMENT_LINK_ID")
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        os.environ["NAMENGINE_PET_STRIPE_PAYMENT_LINK_ID"] = "plink_pet"
        try:
            with patch(
                "app._stripe_api_get",
                return_value={
                    "payment_status": "paid",
                    "status": "complete",
                    "payment_link": "plink_pet",
                    "client_reference_id": session_id,
                    "metadata": {},
                },
            ):
                paid_return = returning_client.get(
                    "/pet/access?checkout_session_id=cs_test_paid",
                    follow_redirects=False,
                )
        finally:
            if previous_secret is None:
                os.environ.pop("STRIPE_SECRET_KEY", None)
            else:
                os.environ["STRIPE_SECRET_KEY"] = previous_secret
            if previous_link_id is None:
                os.environ.pop("NAMENGINE_PET_STRIPE_PAYMENT_LINK_ID", None)
            else:
                os.environ["NAMENGINE_PET_STRIPE_PAYMENT_LINK_ID"] = previous_link_id

        self.assertEqual(paid_return.status_code, 302)
        self.assertEqual(paid_return.headers["Location"], f"/results/session/{session_id}")

    def test_paid_checkout_return_recovers_prior_list_from_stripe_metadata(self):
        from app import _signed_beta_access_token, beta_pending_cookie_name

        first = self.client.get(f"/pet/results?{self._first_query_for('pet')}")
        session_id = self._extract_session_id(first.get_data(as_text=True))
        vertical = get_vertical("pet")
        returning_client = create_app().test_client()
        returning_client.set_cookie(
            beta_pending_cookie_name(vertical),
            _signed_beta_access_token(vertical),
        )
        previous_secret = os.environ.get("STRIPE_SECRET_KEY")
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        try:
            with patch("app._stripe_checkout_session_paid", return_value=True), patch(
                "app._stripe_api_get",
                return_value={
                    "payment_status": "paid",
                    "status": "complete",
                    "metadata": {
                        "namengine_access": "1",
                        "namengine_vertical": "pet",
                        "namengine_return_session": session_id,
                    },
                },
            ):
                paid_return = returning_client.get(
                    "/pet/access?checkout_session_id=cs_test_paid",
                    follow_redirects=False,
                )
        finally:
            if previous_secret is None:
                os.environ.pop("STRIPE_SECRET_KEY", None)
            else:
                os.environ["STRIPE_SECRET_KEY"] = previous_secret

        self.assertEqual(paid_return.status_code, 302)
        self.assertEqual(paid_return.headers["Location"], f"/results/session/{session_id}")

    def test_paid_checkout_return_recovers_prior_list_from_stripe_without_pending_cookie(self):
        first = self.client.get(f"/baby/results?{self._first_query_for('baby')}")
        session_id = self._extract_session_id(first.get_data(as_text=True))
        returning_client = create_app().test_client()
        previous_secret = os.environ.get("STRIPE_SECRET_KEY")
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_example"
        try:
            with patch(
                "app._stripe_api_get",
                return_value={
                    "payment_status": "paid",
                    "status": "complete",
                    "metadata": {
                        "namengine_access": "1",
                        "namengine_vertical": "baby",
                        "namengine_return_session": session_id,
                    },
                },
            ):
                paid_return = returning_client.get(
                    "/baby/access?checkout_session_id=cs_test_paid",
                    follow_redirects=False,
                    base_url="https://nam-engine.com",
                )
        finally:
            if previous_secret is None:
                os.environ.pop("STRIPE_SECRET_KEY", None)
            else:
                os.environ["STRIPE_SECRET_KEY"] = previous_secret

        paid_cookie = "\n".join(paid_return.headers.getlist("Set-Cookie"))
        paid_access_revisit = returning_client.get(
            "/baby/access",
            follow_redirects=False,
            base_url="https://nam-engine.com",
        )

        self.assertEqual(paid_return.status_code, 302)
        self.assertEqual(paid_return.headers["Location"], f"/results/session/{session_id}")
        self.assertIn("namengine_access_unlocked_baby=", paid_cookie)
        self.assertEqual(paid_access_revisit.status_code, 302)
        self.assertEqual(paid_access_revisit.headers["Location"], f"/results/session/{session_id}")

    def test_optional_email_capture_records_email_without_unlocking_access(self):
        first = self.client.get(f"/baby/results?{self._baby_first_query()}")
        session_id = self._extract_session_id(first.get_data(as_text=True))
        visitor_id = self._visitor_cookie_value()
        self._expire_usage(visitor_id)

        capture = self.client.post(
            "/baby/access/email",
            data={"email": "tester@example.com", "return_session": session_id},
            follow_redirects=False,
        )
        usage = get_beta_usage(visitor_id, "baby")
        blocked = self.client.get(f"/results/session/{session_id}", follow_redirects=False)

        self.assertEqual(capture.status_code, 302)
        self.assertIn("email_saved=1", capture.headers["Location"])
        self.assertEqual(usage["email"], "tester@example.com")
        self.assertEqual(blocked.status_code, 302)
        self.assertIn(f"/baby/access?return_session={session_id}", blocked.headers["Location"])


if __name__ == "__main__":
    unittest.main()
