import re
import unittest

from app import create_app
from namengine.core.name_facts import build_name_fact_card


class PhaseThirtyBabyPopularitySnapshotTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_popularity_snapshot_uses_rank_count_trend_and_scale(self):
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

        snapshot = card["popularity_snapshot"]
        self.assertEqual("Familiar", snapshot["current_feel"])
        self.assertIn("#277", snapshot["latest"])
        self.assertIn("1,140 births", snapshot["latest"])
        self.assertIn("Fairly steady", snapshot["trend"])
        self.assertIn("15,895", snapshot["scale"])

    def test_chosen_card_renders_structured_popularity_not_vague_paragraph(self):
        results_response = self.client.get(
            "/baby/results",
            query_string={
                "gender": "Girl",
                "family_context": "african american",
                "cultural_heritage": "African",
                "style": "Modern",
                "sound": "Bright",
            },
        )
        session_id = re.search(r'data-session-id="([^"]+)"', results_response.get_data(as_text=True)).group(1)
        chosen_response = self.client.post(
            "/choose",
            data={"session_id": session_id, "result_id": "baby-1"},
            follow_redirects=True,
        )
        text = chosen_response.get_data(as_text=True)
        fact_card = re.search(r'<section class="name-fact-card".*?</section>', text, re.S).group(0)

        self.assertIn("Current feel", fact_card)
        self.assertIn("Latest data", fact_card)
        self.assertIn("SSA-recorded total", fact_card)
        self.assertNotIn("Approx. US use: familiar", fact_card)
        self.assertNotIn("likely thousands", fact_card)


if __name__ == "__main__":
    unittest.main()
