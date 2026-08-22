import hashlib
import unittest
from pathlib import Path

from app import create_app


APPROVED_ASSET_HASHES = {
    "app-icon.svg": "fcb3fe0ec6b802a92465d8814e6c628d1a0d82f542961c98b284c737f05b89c6",
    "brand-tokens.json": "97edd56a57be79a22dcf0abc2f52e6c9f9d3ef393cb2f72fb8cee6fe24d3189b",
    "favicon.svg": "7a3a300ea516ae4948e3926c0f27ccf8ca7076d1f5e3c450ef0844c99b30d03c",
    "namengine-baby-icon.svg": "7cd9d98f601a90ac5d33c7eea77e4f5833357110653e5c6f0715dafb8cd343d1",
    "namengine-baby.svg": "24bbf2b385585f03f2c38521aab963ea00db2faf00d42360d435f4b27fdbbbda",
    "namengine-biz-icon.svg": "521d0795e1d3615df0d89c9bc3d28afc3705d3ceba8dbee70f34711289e288c9",
    "namengine-biz.svg": "98258edc80d7b8c72dc114850a12ad9386964838bbef78c31dbe7409f03a7421",
    "namengine-icon.svg": "7a3a300ea516ae4948e3926c0f27ccf8ca7076d1f5e3c450ef0844c99b30d03c",
    "namengine-pets-icon.svg": "3e778d5d03d189e8595d874583f708533a513066e591277d7501e819e5b55d89",
    "namengine-pets.svg": "4015cd63769a6728263c0dd084813e3fbef735de9f094050d8ae1a8ed2b72218",
    "namengine.svg": "7d2e6e89b0a95bfb38919db185fac286f76a7f41bbc951111727250162524a39",
}

RETIRED_PET_LOGO_ASSETS = {
    "pet-logo.svg",
    "pet-share.svg",
    "pet/namengine-pet-card-logo.png",
    "pet/namengine-pet-logo-transparent.png",
    "pet/namengine-pet-logo.jpg",
    "pet/namengine-pet-logo.png",
}


class ApprovedBrandingAssetsTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        self.image_root = Path(self.app.static_folder) / "images"

    def test_production_assets_match_approved_hashes(self):
        for filename, expected_hash in APPROVED_ASSET_HASHES.items():
            with self.subTest(filename=filename):
                asset = self.image_root / filename
                self.assertTrue(asset.is_file(), asset)
                self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), expected_hash)

    def test_retired_pet_logo_assets_are_not_in_active_static_images(self):
        for filename in RETIRED_PET_LOGO_ASSETS:
            with self.subTest(filename=filename):
                self.assertFalse((self.image_root / filename).exists())

    def test_shared_pages_render_master_logo_and_approved_icons(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('/static/images/namengine.svg', body)
        self.assertIn('rel="icon" type="image/svg+xml" href="/static/images/favicon.svg"', body)
        self.assertIn('rel="apple-touch-icon" href="/static/images/app-icon.svg"', body)
        self.assertNotIn("home-brand-mark", body)
        self.assertNotIn("<span>NamEngine</span>", body)

    def test_baby_pages_use_shared_header_and_approved_baby_share_asset(self):
        response = self.client.get("/baby")
        body = response.get_data(as_text=True)
        header = body.split("</header>", 1)[0]

        self.assertEqual(response.status_code, 200)
        self.assertIn('brand-home-link', header)
        self.assertIn('aria-label="Home"', header)
        self.assertIn('class="brand-home-text">Home</span>', header)
        self.assertIn('/static/images/baby/namengine-baby-share.png', body)
        welcome = body.split('<div class="baby-welcome">', 1)[1].split('<div class="hero-actions">', 1)[0]
        self.assertIn('/static/images/namengine-baby.svg', welcome)
        self.assertIn('class="vertical-page-logo', welcome)
        self.assertNotIn('class="baby-interview-brand', body)
        self.assertNotIn("images/baby/namengine-baby-logo.png", body)
        self.assertNotIn("images/baby/namengine-baby-logo.svg", body)

    def test_pet_uses_approved_pets_mark_and_business_keeps_existing_logo(self):
        pet = self.client.get("/pet").get_data(as_text=True)
        business = self.client.get("/business").get_data(as_text=True)

        self.assertIn("images/namengine-pets.svg", pet)
        self.assertNotIn("images/namengine-pets-icon.svg", pet)
        self.assertNotIn("images/pet/namengine-pet-logo-transparent.png", pet)
        self.assertIn("images/pet/namengine-pet-share-current.png", pet)
        self.assertIn("images/namengine-biz.svg", business)
        self.assertIn("images/business/namengine-business-share-current.png", business)
        self.assertNotIn("images/namengine-biz-icon.svg", business)


if __name__ == "__main__":
    unittest.main()
