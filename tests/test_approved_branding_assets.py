import hashlib
import unittest
from pathlib import Path

from app import create_app


APPROVED_ASSET_HASHES = {
    "app-icon.svg": "fcb3fe0ec6b802a92465d8814e6c628d1a0d82f542961c98b284c737f05b89c6",
    "brand-tokens.json": "67ec12d0fedfefc97d191f74c6b5abf57a11104b7ebf05a7eaee629a5c9f2dae",
    "favicon.svg": "7a3a300ea516ae4948e3926c0f27ccf8ca7076d1f5e3c450ef0844c99b30d03c",
    "namengine-baby-icon.svg": "7cd9d98f601a90ac5d33c7eea77e4f5833357110653e5c6f0715dafb8cd343d1",
    "namengine-baby.svg": "24bbf2b385585f03f2c38521aab963ea00db2faf00d42360d435f4b27fdbbbda",
    "namengine-biz-icon.svg": "521d0795e1d3615df0d89c9bc3d28afc3705d3ceba8dbee70f34711289e288c9",
    "namengine-biz.svg": "641133ef8f677b9eb412c3a94556bc680b7b68e51d82a936655fb4dd9605af26",
    "namengine-icon.svg": "7a3a300ea516ae4948e3926c0f27ccf8ca7076d1f5e3c450ef0844c99b30d03c",
    "namengine-pets-icon.svg": "efed9e04e4724e06a110d8aa38877edaef7781fafbbe1030e364f3d1dd805ce8",
    "namengine-pets.svg": "5e503cedc68eefe7670e87720cc7e7d44e880382f0c48c211ade5e798327eaf8",
    "namengine.svg": "7d2e6e89b0a95bfb38919db185fac286f76a7f41bbc951111727250162524a39",
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

    def test_shared_pages_render_master_logo_and_approved_icons(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('/static/images/namengine.svg', body)
        self.assertIn('rel="icon" type="image/svg+xml" href="/static/images/favicon.svg"', body)
        self.assertIn('rel="apple-touch-icon" href="/static/images/app-icon.svg"', body)
        self.assertNotIn("home-brand-mark", body)
        self.assertNotIn("<span>NamEngine</span>", body)

    def test_baby_pages_render_approved_baby_logo(self):
        response = self.client.get("/baby")
        body = response.get_data(as_text=True)
        header = body.split("</header>", 1)[0]

        self.assertEqual(response.status_code, 200)
        self.assertIn('/static/images/namengine-baby.svg', header)
        self.assertIn('alt="NamEngine Baby"', header)
        self.assertIn('/static/images/namengine-baby.svg', body)
        welcome = body.split('<div class="baby-welcome">', 1)[1].split('<div class="hero-actions">', 1)[0]
        self.assertNotIn('/static/images/namengine-baby.svg', welcome)
        self.assertNotIn("images/baby/namengine-baby-logo.png", body)
        self.assertNotIn("images/baby/namengine-baby-logo.svg", body)

    def test_unfinished_pet_and_business_screens_keep_existing_logos(self):
        pet = self.client.get("/pet").get_data(as_text=True)
        business = self.client.get("/business").get_data(as_text=True)

        self.assertIn("images/pet/namengine-pet-logo-transparent.png", pet)
        self.assertNotIn("images/namengine-pets.svg", pet)
        self.assertIn("images/business/namengine-business-logo.png", business)
        self.assertNotIn("images/namengine-biz.svg", business)


if __name__ == "__main__":
    unittest.main()
