import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app


class MultiVerticalCompletionPassTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                "NAMENGINE_DB_PATH": os.path.join(self.tempdir.name, "test.sqlite3"),
                "OPENAI_API_KEY": "",
                "NAMENGINE_DISABLE_BABY_IMAGES": "1",
                "NAMENGINE_DISABLE_PET_IMAGES": "1",
                "NAMENGINE_DISABLE_BUSINESS_IMAGES": "1",
            },
        )
        self.env.start()
        app = create_app()
        app.testing = True
        self.client = app.test_client()

    def tearDown(self):
        self.env.stop()
        self.tempdir.cleanup()

    def test_three_launch_intakes_share_polish_without_sharing_voice(self):
        expected = {
            "baby": ("Let’s discover your child’s name together.", "Most parents finish in about 3–5 minutes.", "Thoughtful AI guidance"),
            "pet": ("Let’s find the name that feels like them.", "Most pet parents finish in about 3–5 minutes.", "Personality-led suggestions"),
            "business": ("Let’s find a name your business can grow into.", "Most founders finish in about 5–7 minutes.", "Strategic AI guidance"),
        }
        for vertical, phrases in expected.items():
            with self.subTest(vertical=vertical):
                response = self.client.get(f"/{vertical}")
                body = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn("polished-flow-shell", body)
                self.assertIn("Step 1 of 3", body)
                self.assertIn("data-baby-intake-section", body)
                self.assertIn("baby-intake-polish.js", body)
                for phrase in phrases:
                    self.assertIn(phrase, body)

    def test_results_keep_shared_favorites_compare_choose_and_vertical_framing(self):
        routes = {
            "baby": "/baby/results?gender=Girl&style=Classic&sound=Soft",
            "pet": "/pet/results?pet_type=Dog&style=Classic&vibe=Playful",
            "business": "/business/results?business_description=Design+studio&audience=Premium+clients&style=Premium+and+refined",
        }
        for vertical, route in routes.items():
            with self.subTest(vertical=vertical):
                response = self.client.get(route)
                body = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn("data-saved-count", body)
                self.assertIn("Compare favorites", body)
                self.assertIn('action="/choose"', body)
                self.assertIn("Open full detail", body)

    def test_launch_navigation_is_minimal_and_unfinished_routes_remain_available(self):
        home = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="/baby"', home)
        self.assertIn('href="/pet"', home)
        self.assertIn('href="/business"', home)
        self.assertNotIn('href="/product"', home)
        self.assertNotIn('href="/character"', home)
        self.assertNotIn('href="/baby/beta"', home)

        flow_header = self.client.get("/pet").get_data(as_text=True).split("</header>", 1)[0]
        self.assertIn('href="/"', flow_header)
        self.assertIn('href="/privacy"', flow_header)
        self.assertNotIn('href="/business"', flow_header)

        self.assertEqual(self.client.get("/product").status_code, 200)
        self.assertEqual(self.client.get("/character").status_code, 200)
        self.assertEqual(self.client.get("/baby/beta").status_code, 200)

    def test_public_legal_routes_are_unchanged(self):
        for route in ("/privacy", "/terms", "/disclaimers", "/data-protection"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)


if __name__ == "__main__":
    unittest.main()
