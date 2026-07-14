import unittest

from app import create_app
from namengine.core.briefs import build_brief
from namengine.core.generation import generate_names
from namengine.verticals import get_vertical


class PhaseTwentySevenBabyCulturalHeritageDropdownTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app().test_client()
        self.vertical = get_vertical("baby")

    def test_baby_intake_renders_optional_cultural_heritage_dropdown(self):
        response = self.app.get("/baby")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('name="cultural_heritage"', text)
        self.assertIn("Cultural / heritage feel", text)
        self.assertIn('value="No preference" selected', text)
        self.assertIn("Native American / Indigenous", text)
        self.assertIn("International / blended", text)
        self.assertIn("Something else", text)
        self.assertIn("specific nation or community", text)

    def test_no_preference_is_non_required_and_does_not_create_heritage_bias(self):
        brief = build_brief(
            self.vertical,
            {
                "gender": "Boy",
                "style": "Classic",
                "sound": "Warm",
                "cultural_heritage": "No preference",
            },
        )
        results = generate_names(self.vertical, brief, use_ai=False)
        names = [item.name for item in results[:6]]

        self.assertIn("No preference", brief.inputs["cultural_heritage"])
        self.assertNotEqual(names[:3], ["Giovanni", "Leonardo", "Lorenzo"])

    def test_cultural_heritage_dropdown_can_drive_heritage_results_without_notes(self):
        brief = build_brief(
            self.vertical,
            {
                "gender": "Boy",
                "style": "Classic",
                "sound": "Warm",
                "cultural_heritage": "Italian",
            },
        )
        results = generate_names(self.vertical, brief, use_ai=False)
        names = [item.name for item in results[:6]]

        self.assertIn("Italian", brief.inputs["cultural_heritage"])
        italian_lane = {
            "Giovanni",
            "Santino",
            "Matteo",
            "Luca",
            "Leonardo",
            "Lorenzo",
            "Dante",
            "Marco",
            "Enzo",
            "Alessio",
            "Rocco",
            "Vittorio",
            "Elio",
        }
        self.assertGreaterEqual(len(italian_lane & set(names)), 6)


if __name__ == "__main__":
    unittest.main()
