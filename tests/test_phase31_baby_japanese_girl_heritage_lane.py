import unittest

from app import create_app
from namengine.core.briefs import build_brief
from namengine.core.generation import generate_names, _requested_heritage_groups
from namengine.verticals import get_vertical


class PhaseThirtyOneBabyJapaneseGirlHeritageLaneTest(unittest.TestCase):
    def setUp(self):
        create_app()
        self.vertical = get_vertical("baby")

    def _brief(self):
        return build_brief(
            self.vertical,
            {
                "gender": "Girl",
                "style": "Playful",
                "cultural_heritage": "Japanese",
            },
        )

    def test_japanese_heritage_is_detected_for_girl_playful_request(self):
        self.assertIn("japanese", _requested_heritage_groups(self._brief()))

    def test_playful_japanese_girl_request_returns_japanese_lane_names(self):
        results = generate_names(self.vertical, self._brief(), use_ai=False)
        first_names = [result.name for result in results[:8]]
        expected_lane = {
            "Sakura",
            "Hana",
            "Yumi",
            "Emi",
            "Aiko",
            "Mei",
            "Rina",
            "Kiko",
            "Mika",
            "Noa",
            "Yuna",
            "Hina",
            "Sora",
            "Haru",
        }

        self.assertGreaterEqual(len(set(first_names) & expected_lane), 6, first_names)
        self.assertNotEqual(first_names[:6], ["Clara", "Romy", "Tessa", "Daphne", "Rhea", "Blythe"])


if __name__ == "__main__":
    unittest.main()
