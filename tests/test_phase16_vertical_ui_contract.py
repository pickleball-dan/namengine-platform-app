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
        self.assertIn("images/pet/namengine-pet-logo.png", body)
        self.assertIn("identity-preview", body)
        self.assertIn("og:image", body)
        self.assertIn("--accent: #2f9486", body)
        self.assertIn("--accent-pet: #fcba76", body)

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

    def test_results_direction_items_link_back_to_prefilled_intake_fields(self):
        response = self.client.get(
            "/pet/results?pet_type=Dog&style=Classic&vibe=Playful&partner_alignment=cute"
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="brief-summary direction-disclosure"', body)
        self.assertIn("<summary>", body)
        self.assertIn("Your direction", body)
        self.assertIn("selections", body)
        self.assertIn('class="brief-summary-item"', body)
        self.assertIn("/pet?pet_type=Dog&amp;style=Classic&amp;vibe=Playful", body)
        self.assertIn("edit=style", body)
        self.assertNotIn('class="refine-panel"', body)

        edit_response = self.client.get("/pet?pet_type=Dog&style=Classic&vibe=Playful&edit=style")
        edit_body = edit_response.get_data(as_text=True)

        self.assertEqual(edit_response.status_code, 200)
        self.assertIn('class="field is-edit-target"', edit_body)
        self.assertIn('<option value="Classic" selected>Classic</option>', edit_body)

    def test_intake_sections_have_visible_group_treatment(self):
        css_path = Path(self.app.static_folder) / "css" / "platform.css"
        css = css_path.read_text(encoding="utf-8")

        self.assertIn("counter-reset: intake-section", css)
        self.assertIn("counter-increment: intake-section", css)
        self.assertIn("font-size: 25px", css)
        self.assertIn(".intake-section:nth-of-type(2)", css)
        self.assertIn(".intake-section:nth-of-type(3)", css)
        self.assertIn(".brief-summary-item:hover", css)
        self.assertIn(".direction-disclosure summary", css)
        self.assertIn(".field.is-edit-target", css)

    def test_reaction_selected_state_uses_soft_pet_highlight(self):
        css_path = Path(self.app.static_folder) / "css" / "platform.css"
        css = css_path.read_text(encoding="utf-8")

        self.assertIn(".reaction-row button.is-selected", css)
        self.assertIn("background: rgba(47, 148, 134, 0.16)", css)
        self.assertIn("box-shadow: 0 0 0 3px rgba(252, 186, 118, 0.26)", css)
        self.assertNotIn(
            ".reaction-row button:hover,\n.reaction-row button.is-selected",
            css,
        )


if __name__ == "__main__":
    unittest.main()
