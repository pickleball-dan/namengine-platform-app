import os
from unittest.mock import patch


def csrf_token(client):
    """Return the CSRF token currently set on the test client's cookie jar.

    The app sets this cookie on every page render (see base.html). Call this
    after any GET request in the test (or after unlock_beta_access, which
    itself follows a GET) and include the result as "csrf_token" in POST
    payloads to /choose, /refine, and /api/react.
    """
    cookie = client.get_cookie("namengine_csrf")
    return cookie.value if cookie else ""


def unlock_beta_access(client, vertical_slug="baby"):
    """Simulate the verified checkout return used by paid refinement tests.

    Note: beta_landing (the checkout-return route) legitimately redirects straight
    to an existing results session (302) instead of rendering a generic unlocked
    page (200) when a prior session exists — this is intentional product behavior
    ("Return to results after verified checkout"), not a bug. follow_redirects=True
    ensures the helper resolves through that redirect rather than hard-failing on it.
    """
    env_key = f"NAMENGINE_{vertical_slug.upper()}_BETA_PAYMENT_LINK"
    previous = os.environ.get(env_key)
    os.environ[env_key] = "https://buy.stripe.com/test_example"
    try:
        checkout = client.get(f"/{vertical_slug}/access/checkout")
        if checkout.status_code not in {302, 303}:
            raise AssertionError(f"checkout did not redirect: {checkout.status_code}")
        with patch("app._stripe_checkout_session_paid", return_value=True):
            paid_return = client.get(
                f"/{vertical_slug}/access?checkout_session_id=cs_test_paid",
                follow_redirects=True,
            )
        if paid_return.status_code != 200:
            raise AssertionError(f"paid return did not render: {paid_return.status_code}")
    finally:
        if previous is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = previous
