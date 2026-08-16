import re
import unittest
from urllib.parse import urlparse

from app import create_app
from namengine.verticals import VERTICALS


META_ROUTES = (
    "/",
    "/baby",
    "/pet",
    "/business",
    "/baby/access",
    "/pet/access",
    "/business/access",
)


class ShareMetadataTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def _body(self, path):
        response = self.client.get(path, base_url="https://nam-engine.com")
        self.assertEqual(response.status_code, 200, path)
        return response.get_data(as_text=True)

    def _meta_content(self, body, name):
        patterns = (
            rf'<meta property="{re.escape(name)}" content="([^"]+)">',
            rf'<meta name="{re.escape(name)}" content="([^"]+)">',
        )
        for pattern in patterns:
            match = re.search(pattern, body)
            if match:
                return match.group(1)
        self.fail(f"Missing meta tag {name}")

    def test_public_pages_have_complete_preview_metadata(self):
        for route in META_ROUTES:
            with self.subTest(route=route):
                body = self._body(route)
                self.assertIn('<meta property="og:type" content="website">', body)
                self.assertIn('<meta property="og:site_name" content="NamEngine">', body)
                self.assertIn('<meta name="twitter:card" content="summary_large_image">', body)
                self.assertTrue(self._meta_content(body, "og:title"))
                self.assertTrue(self._meta_content(body, "og:description"))
                self.assertTrue(self._meta_content(body, "twitter:title"))
                self.assertTrue(self._meta_content(body, "twitter:description"))
                self.assertEqual(self._meta_content(body, "og:image"), self._meta_content(body, "twitter:image"))
                self.assertEqual(self._meta_content(body, "og:image"), self._meta_content(body, "og:image:secure_url"))
                self.assertEqual(self._meta_content(body, "og:image:width"), "1200")
                self.assertEqual(self._meta_content(body, "og:image:height"), "630")

    def test_share_images_are_absolute_preview_safe_raster_assets(self):
        for route in META_ROUTES:
            with self.subTest(route=route):
                body = self._body(route)
                image = self._meta_content(body, "og:image")
                parsed = urlparse(image)
                self.assertEqual(parsed.scheme, "https")
                self.assertEqual(parsed.netloc, "nam-engine.com")
                self.assertRegex(parsed.path, r"\.(png|jpg|jpeg)$")
                self.assertNotRegex(parsed.path, r"\.svg$")

    def test_vertical_share_images_use_existing_raster_cards(self):
        expected = {
            "baby": "/static/images/baby/namengine-baby-share.png",
            "pet": "/static/images/pet/namengine-pet-share-current.png",
            "business": "/static/images/business/namengine-business-share-current.png",
        }
        for slug, path in expected.items():
            with self.subTest(slug=slug):
                self.assertEqual(VERTICALS[slug].assets["share_image"], path.removeprefix("/static/"))
                body = self._body(f"/{slug}")
                self.assertIn(path, self._meta_content(body, "og:image"))


if __name__ == "__main__":
    unittest.main()
