import unittest
from pathlib import Path

from app import create_app
from namengine.core import (
    REQUIRED_ASSET_KEYS,
    REQUIRED_THEME_KEYS,
    validate_vertical_ui_contract,
    vertical_theme_style,
)
from namengine.verticals import VERTICALS


class PhaseSixteenVerticalUiContractTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def test_every_vertical_has_complete_ui_contract(self):
        for vertical in VERTICALS.values():
            with self.subTest(vertical=vertical.slug):
                self.assertFalse(
                    validate_vertical_ui_contract(vertical, self.app.static_folder)
                )
                self.assertTrue(set(REQUIRED_THEME_KEYS) <= set(vertical.theme))
                self.assertTrue(set(REQUIRED_ASSET_KEYS) <= set(vertical.assets))

    def test_vertical_theme_style_exports_css_variables(self):
        style = vertical_theme_style(VERTICALS["pet"])

        self.assertIn("--accent:", style)
        self.assertIn("--surface:", style)
        self.assertIn("--page:", style)
        self.assertIn("--card:", style)

    def test_vertical_assets_exist_on_disk(self):
        for vertical in VERTICALS.values():
            with self.subTest(vertical=vertical.slug):
                for asset_key in REQUIRED_ASSET_KEYS:
                    asset_path = Path(self.app.static_folder) / vertical.assets[asset_key]
                    self.assertTrue(asset_path.is_file(), asset_path)

    def test_pet_pages_use_vertical_logo_and_theme(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("vertical-pet", body)
        self.assertIn("images/pet-logo.svg", body)
        self.assertIn("--accent: #f2b84b", body)

    def test_pet_intake_matches_first_edition_question_contract(self):
        questions = {question.id: question for question in VERTICALS["pet"].intake_questions}

        self.assertEqual(
            list(questions),
            [
                "pet_type",
                "pet_gender",
                "notes",
                "discovery_style",
                "style",
                "timeless_vs_distinctive",
                "familiarity_preference",
                "pronunciation_importance",
                "vibe",
                "cultural_context",
                "partner_alignment",
            ],
        )
        self.assertIn("Dog", questions["pet_type"].choices)
        self.assertIn("Balanced mix", questions["discovery_style"].choices)
        self.assertIn("Very important", questions["pronunciation_importance"].choices)
        self.assertIn("Nature", questions["cultural_context"].choices)
        self.assertEqual(questions["notes"].kind, "textarea")
        self.assertEqual(questions["partner_alignment"].kind, "textarea")
        self.assertTrue(questions["pet_type"].required)
        self.assertTrue(questions["style"].required)
        self.assertTrue(questions["vibe"].required)
        self.assertEqual(questions["pet_type"].section, "About your pet")
        self.assertEqual(questions["style"].section, "Name style")
        self.assertEqual(questions["vibe"].section, "Fit and feeling")

    def test_pet_intake_renders_as_three_decision_sections(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("About your pet", body)
        self.assertIn("Name style", body)
        self.assertIn("Fit and feeling", body)
        self.assertIn("Optional", body)


if __name__ == "__main__":
    unittest.main()
