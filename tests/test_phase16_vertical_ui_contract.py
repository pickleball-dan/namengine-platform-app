import unittest
import struct
import zlib
from pathlib import Path

from app import create_app
from namengine.core import (
    REQUIRED_ASSET_KEYS,
    REQUIRED_THEME_KEYS,
    validate_vertical_ui_contract,
    vertical_theme_style,
)
from namengine.verticals import VERTICALS


def _png_rgba_size_and_corner_alpha(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path} is not a PNG")

    offset = 8
    width = height = color_type = interlace = None
    idat = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if bit_depth != 8 or color_type != 6 or interlace != 0:
                raise AssertionError(f"{path} must be a non-interlaced 8-bit RGBA PNG")
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None:
        raise AssertionError(f"{path} has no IHDR")

    raw = zlib.decompress(bytes(idat))
    stride = width * 4
    rows = []
    previous = [0] * stride
    cursor = 0
    for _row in range(height):
        filter_type = raw[cursor]
        cursor += 1
        scanline = list(raw[cursor : cursor + stride])
        cursor += stride
        reconstructed = []
        for i, value in enumerate(scanline):
            left = reconstructed[i - 4] if i >= 4 else 0
            up = previous[i]
            up_left = previous[i - 4] if i >= 4 else 0
            if filter_type == 0:
                decoded = value
            elif filter_type == 1:
                decoded = value + left
            elif filter_type == 2:
                decoded = value + up
            elif filter_type == 3:
                decoded = value + ((left + up) // 2)
            elif filter_type == 4:
                predictor = left + up - up_left
                pa = abs(predictor - left)
                pb = abs(predictor - up)
                pc = abs(predictor - up_left)
                decoded = value + (left if pa <= pb and pa <= pc else up if pb <= pc else up_left)
            else:
                raise AssertionError(f"{path} uses unsupported PNG filter {filter_type}")
            reconstructed.append(decoded & 0xFF)
        rows.append(reconstructed)
        previous = reconstructed

    corners = [
        rows[0][3],
        rows[0][stride - 1],
        rows[-1][3],
        rows[-1][stride - 1],
    ]
    return width, height, color_type, corners


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

    def test_pet_logo_asset_is_transparent_png(self):
        logo_path = Path(self.app.static_folder) / VERTICALS["pet"].assets["logo"]
        data = logo_path.read_bytes()

        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(data[25], 6)

    def test_pet_pages_use_vertical_logo_and_theme(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("vertical-pet", body)
        self.assertIn("images/pet/namengine-pet-logo-transparent.png", body)
        self.assertIn("identity-preview", body)
        self.assertIn("og:image", body)
        self.assertIn("--accent: #2f9486", body)
        self.assertIn("--accent-pet: #fcba76", body)

    def test_baby_pages_use_full_wordmark_logo(self):
        response = self.client.get("/baby")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("vertical-baby", body)
        self.assertIn("images/baby/namengine-baby-logo.png", body)
        self.assertIn('alt="NamEngine Baby logo"', body)
        self.assertIn("identity-preview", body)

    def test_baby_page_logo_matches_pet_transparent_png_canvas(self):
        static_root = Path(self.app.static_folder)
        baby_logo = static_root / VERTICALS["baby"].assets["page_logo"]
        pet_logo = static_root / VERTICALS["pet"].assets["logo"]

        baby_width, baby_height, baby_color_type, baby_corner_alpha = (
            _png_rgba_size_and_corner_alpha(baby_logo)
        )
        pet_width, pet_height, _pet_color_type, _pet_corner_alpha = (
            _png_rgba_size_and_corner_alpha(pet_logo)
        )

        self.assertEqual(baby_color_type, 6)
        self.assertEqual((baby_width, baby_height), (pet_width, pet_height))
        self.assertEqual(baby_corner_alpha, [0, 0, 0, 0])

    def test_pet_intake_matches_first_edition_question_contract(self):
        questions = {question.id: question for question in VERTICALS["pet"].intake_questions}

        self.assertEqual(
            list(questions),
            [
                "pet_type",
                "pet_gender",
                "pet_breed",
                "pet_color",
                "pet_life_stage",
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
        self.assertIn("Young", questions["pet_life_stage"].choices)
        self.assertIn("Mature", questions["pet_life_stage"].choices)
        self.assertNotIn("Puppy", questions["pet_life_stage"].choices)
        self.assertNotIn("Adult", questions["pet_life_stage"].choices)
        self.assertNotIn("Senior", questions["pet_life_stage"].choices)
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

    def test_baby_intake_requires_one_signal_per_section(self):
        questions = {question.id: question for question in VERTICALS["baby"].intake_questions}

        self.assertTrue(questions["gender"].required)
        self.assertTrue(questions["style"].required)
        self.assertTrue(questions["sound"].required)
        self.assertEqual(questions["gender"].section, "About your baby")
        self.assertEqual(questions["style"].section, "Name style")
        self.assertEqual(questions["sound"].section, "Fit and feeling")

        required_by_section = {}
        for question in VERTICALS["baby"].intake_questions:
            if question.required:
                required_by_section.setdefault(question.section, []).append(question.id)

        self.assertEqual(
            required_by_section,
            {
                "About your baby": ["gender"],
                "Name style": ["style"],
                "Fit and feeling": ["sound"],
            },
        )

    def test_pet_intake_other_dropdown_has_custom_entry_field(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-other-select="pet_type_other"', body)
        self.assertIn('id="pet_type_other"', body)
        self.assertIn('name="pet_type_other"', body)
        self.assertIn('placeholder="Enter your own"', body)

    def test_pet_intake_prefills_custom_other_value_for_editing(self):
        response = self.client.get("/pet?pet_type=Goat&style=Classic&vibe=Playful&edit=pet_type")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('<option value="Other" selected>Other</option>', body)
        self.assertIn('id="pet_type_other"', body)
        self.assertIn('value="Goat"', body)
        self.assertNotIn('id="pet_type_other" name="pet_type_other" data-other-input placeholder="Enter your own" value="Goat" hidden disabled', body)

    def test_pet_intake_renders_as_three_decision_sections(self):
        response = self.client.get("/pet")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("About your pet", body)
        self.assertIn("Name style", body)
        self.assertIn("Fit and feeling", body)
        self.assertIn("Optional", body)
        self.assertIn("Taste history", body)
        self.assertIn("Open taste history", body)
        self.assertIn("Pick up where you left off.", body)
        self.assertIn("data-taste-history-drawer-list", body)
        self.assertIn("data-taste-history-clear", body)
        self.assertIn('data-taste-vertical="pet"', body)

    def test_results_direction_items_link_back_to_prefilled_intake_fields(self):
        response = self.client.get(
            "/pet/results?pet_type=Dog&style=Classic&vibe=Playful&partner_alignment=cute"
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="brief-summary direction-disclosure"', body)
        self.assertIn('data-taste-vertical="pet"', body)
        self.assertIn('data-taste-session-id=', body)
        self.assertIn('data-taste-list-url=', body)
        self.assertIn('data-taste-share-url=', body)
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
        self.assertIn(".taste-history-dialog", css)
        self.assertIn(".taste-history-actions", css)

    def test_pet_taste_history_script_restores_resume_and_view_actions(self):
        js_path = Path(self.app.static_folder) / "js" / "taste-history.js"
        js = js_path.read_text(encoding="utf-8")

        self.assertIn("namengine.pet.tasteHistory.v1", js)
        self.assertIn("namengine.${verticalSlug}.tasteHistory.v1", js)
        self.assertIn("data-taste-history-clear", js)
        self.assertIn("Clear saved ${verticalName} loved names and searches", js)
        self.assertIn("clearLegacyVerticalHistory", js)
        self.assertIn("window.NamEngineTasteHistory", js)
        self.assertIn("data-taste-session-id", js)
        self.assertIn("Resume", js)
        self.assertIn("View list", js)
        self.assertIn("lovedNames", js)

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
