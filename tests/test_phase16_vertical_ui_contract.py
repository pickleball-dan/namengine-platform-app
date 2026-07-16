import unittest
import struct
import zlib
import os
from pathlib import Path
from unittest.mock import patch

from app import create_app
from namengine.core import (
    REQUIRED_ASSET_KEYS,
    REQUIRED_THEME_KEYS,
    REQUIRED_VISUAL_FIELDS,
    build_brief,
    generate_names,
    validate_vertical_ui_contract,
    vertical_theme_style,
)
from namengine.core.domain_availability import (
    build_domain_info,
    domain_slug,
    domain_status_from_godaddy,
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


def _png_opaque_color_pixel_count(path, box, color):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path} is not a PNG")

    offset = 8
    width = height = None
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

    x1, y1, x2, y2 = box
    raw = zlib.decompress(bytes(idat))
    stride = width * 4
    previous = [0] * stride
    cursor = 0
    matching_pixels = 0
    for y in range(height):
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

        if y1 <= y < y2:
            for x in range(x1, x2):
                idx = x * 4
                r, g, b, a = reconstructed[idx : idx + 4]
                if color == "cyan" and a > 0 and r < 80 and g > 120 and b > 120:
                    matching_pixels += 1
                elif color == "red" and a > 0 and r > 170 and g < 140 and b < 150:
                    matching_pixels += 1
        previous = reconstructed

    return matching_pixels


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

    def test_every_vertical_has_visual_launch_config(self):
        for vertical in VERTICALS.values():
            with self.subTest(vertical=vertical.slug):
                for field_name in REQUIRED_VISUAL_FIELDS:
                    self.assertTrue(getattr(vertical.visual, field_name), field_name)

    def test_baby_visual_config_matches_reference_contract(self):
        baby_visual = VERTICALS["baby"].visual

        self.assertEqual(baby_visual.audience, ("expecting parents", "naming partners"))
        self.assertEqual(
            baby_visual.emotional_tone,
            ("tender", "thoughtful", "future-facing"),
        )
        self.assertEqual(baby_visual.hero_message, "Let’s shape the right baby name.")
        self.assertEqual(baby_visual.result_card_style, "practical parent decision card")

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
        self.assertIn("Let’s shape the right pet name.", body)
        self.assertIn("--accent: #2f9486", body)
        self.assertIn("--accent-pet: #fcba76", body)

    def test_baby_pages_use_supplied_baby_logo(self):
        response = self.client.get("/baby")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("vertical-baby", body)
        self.assertIn("images/baby/namengine-baby-logo.png", body)
        self.assertIn("images/baby/namengine-baby-share.png", body)
        self.assertIn('alt="NamEngine Baby logo"', body)
        self.assertIn("identity-preview", body)
        self.assertIn("Let’s shape the right baby name.", body)
        self.assertIn("Built for names that feel tender now and substantial later.", body)
        self.assertIn("Family fit", body)

    def test_business_pages_use_business_graphics_and_copy(self):
        response = self.client.get("/business")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("vertical-business", body)
        self.assertIn("images/business/namengine-business-logo.png", body)
        self.assertIn("images/business/namengine-business-share.png", body)
        self.assertIn("Find a name your business can grow into.", body)
        self.assertIn("Category fit", body)
        self.assertIn("Memorability", body)
        self.assertIn("Launch risk", body)
        self.assertIn("--accent: #27476e", body)
        self.assertIn("--accent-pet: #d9a441", body)

    def test_product_pages_use_visual_contract_copy(self):
        response = self.client.get("/product")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("vertical-product", body)
        self.assertIn("images/product/namengine-product-logo.png", body)
        self.assertIn("images/product/namengine-product-share.png", body)
        self.assertIn("Find a name your product can wear in the real world.", body)
        self.assertIn("Built for names that work on a package, listing, and first impression.", body)
        self.assertIn("Shelf clarity", body)
        self.assertIn("--accent: #b8654b", body)
        self.assertIn("--accent-pet: #e3b04f", body)

    def test_character_pages_use_visual_contract_copy(self):
        response = self.client.get("/character")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Find a name that belongs in the story.", body)
        self.assertIn("Built for names that match role, world, and reader memory.", body)
        self.assertIn("World fit", body)

    def test_home_page_uses_vertical_graphics_system(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("launch-hero", body)
        self.assertIn("launch-baby-card", body)
        self.assertIn("launch-future-grid", body)
        self.assertIn("images/pet/namengine-pet-logo-transparent.png", body)
        self.assertIn("images/baby/namengine-baby-logo.png", body)
        self.assertIn("images/business/namengine-business-logo.png", body)
        self.assertIn("images/product/namengine-product-logo.png", body)
        self.assertIn("images/character-logo.svg", body)
        self.assertIn("Find the name that feels right.", body)
        self.assertIn("Start Baby Naming", body)
        self.assertIn("Available now", body)
        self.assertEqual(body.count("Coming soon"), 4)
        self.assertNotIn("Shared product system", body)

    def test_home_page_cards_use_visual_config_copy(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Thoughtfully chosen names inspired by your family’s story", body)
        self.assertIn("it belonged to your child all along", body)
        self.assertIn("Baby names that fit your family.", body)
        self.assertIn('href="/baby"', body)
        self.assertNotIn('href="/pet" aria-label="NamEngine Pet"', body)
        self.assertNotIn("shared intake", body.lower())
        self.assertNotIn("shared results", body.lower())

    def test_home_page_graphics_have_css_contract(self):
        css_path = Path(self.app.static_folder) / "css" / "platform.css"
        css = css_path.read_text(encoding="utf-8")

        self.assertIn(".launch-hero", css)
        self.assertIn(".launch-baby-card", css)
        self.assertIn(".launch-future-grid", css)
        self.assertIn(".launch-primary-cta", css)

    def test_baby_graphics_follow_pet_asset_slots(self):
        response = self.client.get("/baby")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("header_logo", VERTICALS["baby"].assets)
        self.assertNotIn("card_logo", VERTICALS["baby"].assets)
        self.assertNotIn("page_logo", VERTICALS["baby"].assets)
        self.assertNotIn("brand-logo-wordmark", body)
        header = body.split("</header>", 1)[0]
        self.assertIn("images/baby/namengine-baby-logo.png", header)
        self.assertIn("<span>NamEngine</span>", header)

    def test_business_graphics_follow_pet_asset_slots(self):
        response = self.client.get("/business")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("header_logo", VERTICALS["business"].assets)
        self.assertNotIn("card_logo", VERTICALS["business"].assets)
        self.assertNotIn("page_logo", VERTICALS["business"].assets)
        self.assertNotIn("brand-logo-wordmark", body)
        header = body.split("</header>", 1)[0]
        self.assertIn("images/business/namengine-business-logo.png", header)
        self.assertIn("<span>NamEngine</span>", header)

    def test_product_graphics_follow_pet_asset_slots(self):
        response = self.client.get("/product")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("header_logo", VERTICALS["product"].assets)
        self.assertNotIn("card_logo", VERTICALS["product"].assets)
        self.assertNotIn("page_logo", VERTICALS["product"].assets)
        self.assertNotIn("brand-logo-wordmark", body)
        header = body.split("</header>", 1)[0]
        self.assertIn("images/product/namengine-product-logo.png", header)
        self.assertIn("<span>NamEngine</span>", header)
        self.assertIn("data-taste-vertical=\"product\"", body)

    def test_baby_logo_is_transparent_png_with_baby_mark(self):
        static_root = Path(self.app.static_folder)
        baby_logo = static_root / VERTICALS["baby"].assets["logo"]

        baby_width, baby_height, baby_color_type, baby_corner_alpha = (
            _png_rgba_size_and_corner_alpha(baby_logo)
        )

        self.assertEqual(baby_color_type, 6)
        self.assertGreater(baby_width, 500)
        self.assertGreater(baby_height, 450)
        self.assertEqual(baby_corner_alpha, [0, 0, 0, 0])

        self.assertGreater(
            _png_opaque_color_pixel_count(baby_logo, (310, 165, 520, 330), "red"),
            1000,
        )

    def test_business_logo_is_transparent_png(self):
        static_root = Path(self.app.static_folder)
        business_logo = static_root / VERTICALS["business"].assets["logo"]

        width, height, color_type, corner_alpha = _png_rgba_size_and_corner_alpha(
            business_logo
        )

        self.assertEqual(color_type, 6)
        self.assertGreater(width, 500)
        self.assertGreater(height, 450)
        self.assertEqual(corner_alpha, [0, 0, 0, 0])

    def test_product_logo_is_transparent_png_with_product_mark(self):
        static_root = Path(self.app.static_folder)
        product_logo = static_root / VERTICALS["product"].assets["logo"]

        width, height, color_type, corner_alpha = _png_rgba_size_and_corner_alpha(
            product_logo
        )

        self.assertEqual(color_type, 6)
        self.assertGreater(width, 500)
        self.assertGreater(height, 450)
        self.assertEqual(corner_alpha, [0, 0, 0, 0])
        self.assertGreater(
            _png_opaque_color_pixel_count(product_logo, (60, 70, 190, 205), "cyan"),
            1000,
        )

    def test_baby_page_logo_contains_namengine_cyan_mark(self):
        static_root = Path(self.app.static_folder)
        baby_logo = static_root / VERTICALS["baby"].assets["logo"]

        self.assertGreater(
            _png_opaque_color_pixel_count(baby_logo, (0, 190, 220, 360), "cyan"),
            1000,
        )

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

    def test_business_intake_requires_one_signal_per_launch_section(self):
        questions = {question.id: question for question in VERTICALS["business"].intake_questions}

        self.assertTrue(questions["business_description"].required)
        self.assertTrue(questions["audience"].required)
        self.assertTrue(questions["style"].required)
        self.assertEqual(questions["business_description"].section, "About the business")
        self.assertEqual(questions["style"].section, "Name style")
        self.assertEqual(questions["domain_preference"].section, "Launch fit")
        self.assertEqual(questions["business_description"].kind, "textarea")
        self.assertIn("Modern and energetic", questions["style"].choices)
        self.assertIn("Exact .com matters", questions["domain_preference"].choices)

        required_by_section = {}
        for question in VERTICALS["business"].intake_questions:
            if question.required:
                required_by_section.setdefault(question.section, []).append(question.id)

        self.assertEqual(
            required_by_section,
            {
                "About the business": ["business_description", "audience"],
                "Name style": ["style"],
            },
        )

    def test_business_results_use_business_validation_and_labels(self):
        with patch.dict(os.environ, {"GODADDY_API_KEY": "", "GODADDY_API_SECRET": ""}):
            response = self.client.get(
                "/business/results?business_description=AI+operations+consulting"
                "&industry=Consulting&audience=B2B+buyers&style=Clear+and+credible"
            )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Brand fit", body)
        self.assertIn("Launch risks", body)
        self.assertIn("Domain signal", body)
        self.assertIn("Category fit", body)
        self.assertIn("Launch risk", body)
        self.assertIn("Domain quick check", body)
        self.assertIn("Quick GoDaddy check, not guaranteed. Verify before purchase.", body)
        self.assertIn("Not checked", body)
        self.assertNotIn("Validation has not been configured", body)

    def test_product_intake_requires_one_signal_per_shelf_section(self):
        questions = {question.id: question for question in VERTICALS["product"].intake_questions}

        self.assertTrue(questions["product_description"].required)
        self.assertTrue(questions["audience"].required)
        self.assertTrue(questions["style"].required)
        self.assertEqual(questions["product_description"].section, "About the product")
        self.assertEqual(questions["style"].section, "Name style")
        self.assertEqual(questions["sales_channel"].section, "Shelf fit")
        self.assertEqual(questions["product_description"].kind, "textarea")
        self.assertIn("Clear and shelf-ready", questions["style"].choices)
        self.assertIn("Retail shelf", questions["sales_channel"].choices)

        required_by_section = {}
        for question in VERTICALS["product"].intake_questions:
            if question.required:
                required_by_section.setdefault(question.section, []).append(question.id)

        self.assertEqual(
            required_by_section,
            {
                "About the product": ["product_description", "audience"],
                "Name style": ["style"],
            },
        )

    def test_product_results_use_product_validation_and_labels(self):
        response = self.client.get(
            "/product/results?product_description=Reusable+hydration+bottle"
            "&category=Drinkware&audience=Everyday+consumers&style=Clear+and+shelf-ready"
            "&sales_channel=Retail+shelf"
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Product fit", body)
        self.assertIn("Shelf risks", body)
        self.assertIn("Shelf fit", body)
        self.assertIn("Category fit", body)
        self.assertIn("Launch risk", body)
        self.assertIn("Brightpack", body)
        self.assertNotIn("Validation has not been configured", body)
        self.assertNotIn("pet-ready", body)

    def test_product_generation_uses_product_fallback_pool(self):
        brief = build_brief(
            VERTICALS["product"],
            {
                "product_description": "Reusable hydration bottle",
                "category": "Drinkware",
                "audience": "Everyday consumers",
                "style": "Clear and shelf-ready",
            },
        )

        names = generate_names(VERTICALS["product"], brief, use_ai=False)

        self.assertEqual(names[0].name, "Brightpack")
        self.assertEqual(names[0].metadata["source"], "product_fallback")
        self.assertIn("product", names[0].tags)

    def test_business_generation_attaches_domain_quick_check_metadata(self):
        brief = build_brief(
            VERTICALS["business"],
            {
                "business_description": "AI operations consulting",
                "industry": "Consulting",
                "audience": "B2B buyers",
                "style": "Clear and credible",
            },
        )

        with patch.dict(os.environ, {"GODADDY_API_KEY": "", "GODADDY_API_SECRET": ""}):
            names = generate_names(VERTICALS["business"], brief, use_ai=False)

        domain_info = names[0].metadata["domain_info"]
        self.assertEqual(domain_info["primary"], "northmark.com")
        self.assertEqual(domain_info["display_status"]["status"], "not_checked")

    def test_business_domain_slug_and_godaddy_status_mapping(self):
        self.assertEqual(domain_slug("Arc & Anchor"), "arcanchor")
        self.assertEqual(build_domain_info("Signal House")["primary"], "signalhouse.com")
        self.assertEqual(
            domain_status_from_godaddy("signalhouse.com", {"available": True})["status"],
            "available",
        )
        self.assertEqual(
            domain_status_from_godaddy(
                "signalhouse.com",
                {"available": True, "premium": True},
            )["status"],
            "premium",
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
