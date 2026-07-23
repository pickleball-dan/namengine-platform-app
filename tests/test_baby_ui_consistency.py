import unittest
from pathlib import Path

from app import create_app


class BabyUiConsistencyTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_name_inspiration_removes_family_heritage_card_without_changing_input_contract(self):
        body = self.client.get("/baby?edit=cultural_context").get_data(as_text=True)

        self.assertNotIn('data-choice-value="Family heritage"', body)
        self.assertIn('<option value="Family heritage"', body)
        self.assertIn("Answering helps us shape more personal names", body)
        self.assertIn(">Skip</button>", body)
        self.assertNotIn("Skip for now", body)

    def test_baby_reaction_labels_preserve_engine_values(self):
        body = self.client.get("/baby/results?gender=Girl&style=Classic&sound=Soft").get_data(as_text=True)

        self.assertIn('data-reaction-value="love"', body)
        self.assertIn('data-reaction-label="Love it"', body)
        self.assertIn('data-reaction-value="no"', body)
        self.assertIn('data-reaction-label="Not for us"', body)
        self.assertNotIn('data-reaction-value="not_for_us"', body)

    def test_baby_results_detail_and_recovery_use_conversation_language(self):
        result_response = self.client.get("/baby/results?gender=Girl&style=Classic&sound=Soft")
        results = result_response.get_data(as_text=True)
        self.assertIn("Here’s what stood out", results)
        self.assertIn("these names best match your style and preferences", results)
        self.assertIn("You loved 0 names in Round 1", results)
        self.assertIn("using those preferences to refine your next recommendations", results)
        self.assertEqual(results.count('class="result-name-link"'), 8)
        self.assertEqual(results.count('class="result-explore-link"'), 8)
        self.assertIn('>Explore <span aria-hidden="true">→</span></a>', results)
        self.assertIn("Quick view", results)
        self.assertNotIn("Tell me more", results)
        self.assertNotIn("Option 4", results)
        self.assertIn("Would you like another thoughtful list", results)

        session_id = results.split('data-session-id="', 1)[1].split('"', 1)[0]
        detail = self.client.get(f"/baby/name/{session_id}/baby-1").get_data(as_text=True)
        self.assertIn("A closer look", detail)
        self.assertIn("Why this made your list", detail)
        self.assertIn("Next decision", detail)
        self.assertIn("Love this name", detail)
        self.assertIn("Not for us", detail)
        self.assertNotIn("Keep as a maybe", detail)
        self.assertNotIn('data-reaction-value="maybe"', detail)
        self.assertIn('<details class="name-fact-overview">', detail)
        self.assertNotIn('<details class="name-fact-overview" open>', detail)
        self.assertIn("Practical checks", detail)

        missing = self.client.get("/share/baby-missing")
        self.assertEqual(missing.status_code, 410)
        self.assertIn("This list is no longer here", missing.get_data(as_text=True))
        self.assertIn("Start a new baby list", missing.get_data(as_text=True))

    def test_shared_css_defines_responsive_baby_shell_and_focus_states(self):
        css = (Path(self.app.root_path) / "static" / "css" / "platform.css").read_text(encoding="utf-8")

        self.assertIn("Baby conversation system", css)
        self.assertIn(".vertical-baby .results-grid", css)
        self.assertIn("grid-template-columns: repeat(4, minmax(0, 1fr))", css)
        self.assertIn(".vertical-baby .result-explore-link", css)
        self.assertIn(".vertical-baby .result-card.is-expanded", css)
        self.assertIn("grid-template-rows: 18px minmax(82px, auto) minmax(108px, auto) 58px", css)
        self.assertIn(".vertical-baby .reaction-row button:is(:hover, :focus-visible)", css)
        self.assertIn("@media (max-width: 600px)", css)
        self.assertIn("overflow-x: hidden", css)


if __name__ == "__main__":
    unittest.main()
