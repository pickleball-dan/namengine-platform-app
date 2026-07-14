import unittest

from app import create_app
from namengine.core.briefs import build_brief
from namengine.core.generation import generate_names, _requested_heritage_groups
from namengine.core.name_facts import build_name_fact_card
from namengine.verticals import get_vertical


class PhaseTwentyNineBabyAfricanHeritageLaneTest(unittest.TestCase):
    def setUp(self):
        create_app()
        self.vertical = get_vertical("baby")

    def _screenshot_brief(self):
        return build_brief(
            self.vertical,
            {
                "gender": "Girl",
                "family_context": "african american",
                "cultural_heritage": "African",
                "discovery_style": "Classic favorites",
                "style": "Modern",
                "sound": "Bright",
                "inspiration": "Music",
            },
        )

    def test_african_and_african_american_fields_stack_instead_of_canceling(self):
        groups = _requested_heritage_groups(self._screenshot_brief())

        self.assertIn("african", groups)
        self.assertIn("african_american", groups)

    def test_screenshot_intake_returns_african_or_african_american_girl_names(self):
        results = generate_names(self.vertical, self._screenshot_brief(), use_ai=False)
        first_names = [result.name for result in results[:8]]
        expected_lane = {
            "Aaliyah",
            "Imani",
            "Nia",
            "Zora",
            "Sanaa",
            "Ayana",
            "Zahara",
            "Asha",
            "Eshe",
            "Zuri",
            "Amina",
            "Makena",
            "Kenya",
            "Maya",
        }

        self.assertGreaterEqual(len(set(first_names) & expected_lane), 6, first_names)
        self.assertNotEqual(first_names[:6], ["Clara", "Eloise", "Nora", "Iris", "Ada", "Celia"])

    def test_african_heritage_names_have_beta_fact_cards(self):
        card = build_name_fact_card(
            "baby",
            {
                "name": "Zuri",
                "pronunciation": "ZOO-ree",
                "tagline": "Swahili-rooted, bright, and modern with a beautiful meaning.",
                "why_this_name": "Zuri fits the bright modern African heritage direction.",
                "tags": ["bright", "modern", "heritage"],
                "validation": [],
            },
        )

        self.assertIsNotNone(card)
        self.assertIn("Swahili", card["origin_meaning"])
        self.assertIn("Zuri Hall", card["famous_namesakes"])
        self.assertIn("Good", "Good to know")


if __name__ == "__main__":
    unittest.main()
