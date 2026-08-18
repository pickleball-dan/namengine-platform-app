import unittest

from app import create_app


class ProxySecureCookieTest(unittest.TestCase):
    def test_forwarded_https_sets_csrf_cookie_secure(self):
        client = create_app().test_client()

        response = client.get("/", headers={"X-Forwarded-Proto": "https"})

        csrf_cookie = next(
            header
            for header in response.headers.getlist("Set-Cookie")
            if header.startswith("namengine_csrf=")
        )
        self.assertIn("Secure", csrf_cookie)


if __name__ == "__main__":
    unittest.main()
