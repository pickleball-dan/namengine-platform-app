import re
import unittest

from app import create_app
from namengine.core.name_facts import build_name_fact_card


class PhaseTwentyEightBabyNameFactCardTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def _create_baby_results_page(self):
        return self.client.get(
            "/baby/results",
            query_string={
                "gender": "Girl",
                "style": "Classic",
                "sound": "Elegant",
                "cultural_heritage": "No preference",
                "notes": "Warm, classic, not trendy",
            },
        )

    def test_build_name_fact_card_for_known_baby_name(self):
        card = build_name_fact_card(
            "baby",
            {
                "name": "Clara",
                "pronunciation": "KLAIR-uh",
                "tagline": "Clear, classic, and gently bright.",
                "why_this_name": "Clara fits the brief because it is classic and warm.",
                "fit_note": "Best for a classic direction.",
                "tags": ["wearable", "warm", "family-ready"],
                "scores": {"baby_popularity": 0.72},
                "validation": [],
            },
        )

        self.assertIsNotNone(card)
        self.assertIn("Latin", card["origin_meaning"])
        self.assertIn("Clara Barton", card["famous_namesakes"])
        self.assertIn("Claire", card["nicknames_variants"])
        self.assertIn("Good", "Good to know")
        self.assertIn("Approx. US use", card["popularity_snapshot"])

    def test_chosen_baby_page_renders_name_fact_card_without_watch_outs(self):
        results_response = self._create_baby_results_page()
        text = results_response.get_data(as_text=True)
        self.assertEqual(results_response.status_code, 200)
        self.assertIn("Choose", text)

        session_id = re.search(r'data-session-id="([^"]+)"', text).group(1)
        chosen_response = self.client.post(
            "/choose",
            data={"session_id": session_id, "result_id": "baby-1"},
            follow_redirects=True,
        )
        chosen_text = chosen_response.get_data(as_text=True)

        self.assertEqual(chosen_response.status_code, 200)
        self.assertIn("Name card", chosen_text)
        self.assertIn("Meaning & origin", chosen_text)
        self.assertIn("Famous namesakes", chosen_text)
        self.assertIn("Popularity snapshot", chosen_text)
        self.assertIn("Nicknames & variants", chosen_text)
        self.assertIn("Similar names", chosen_text)
        self.assertIn("Good to know", chosen_text)
        fact_card = re.search(r'<section class="name-fact-card".*?</section>', chosen_text, re.S).group(0)
        self.assertNotIn("Pronunciation", fact_card)
        self.assertNotIn("Why it fits your brief", fact_card)
        self.assertNotIn("Watch-outs", chosen_text)
        self.assertNotIn("Potential drawbacks", chosen_text)

    def test_name_detail_page_renders_name_fact_card(self):
        results_response = self._create_baby_results_page()
        session_id = re.search(r'data-session-id="([^"]+)"', results_response.get_data(as_text=True)).group(1)
        response = self.client.get(f"/baby/name/{session_id}/baby-1")
        text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Name card", text)
        self.assertIn("Good to know", text)
        self.assertIn("Popularity snapshot", text)


if __name__ == "__main__":
    unittest.main()
