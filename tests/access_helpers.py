import os
from unittest.mock import patch


def unlock_beta_access(client, vertical_slug="baby"):
    """Simulate the verified checkout return used by paid refinement tests."""
    env_key = f"NAMENGINE_{vertical_slug.upper()}_BETA_PAYMENT_LINK"
    previous = os.environ.get(env_key)
    os.environ[env_key] = "https://buy.stripe.com/test_example"
    try:
        checkout = client.get(f"/{vertical_slug}/access/checkout")
        if checkout.status_code not in {302, 303}:
            raise AssertionError(f"checkout did not redirect: {checkout.status_code}")
        with patch("app._stripe_checkout_session_paid", return_value=True):
            paid_return = client.get(f"/{vertical_slug}/access?checkout_session_id=cs_test_paid")
        if paid_return.status_code != 200:
            raise AssertionError(f"paid return did not render: {paid_return.status_code}")
    finally:
        if previous is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = previous
