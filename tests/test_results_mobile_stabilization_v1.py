import os
import tempfile
import unittest
from pathlib import Path

from app import collapsed_result_meaning, create_app
from namengine.core import (
    build_reaction,
    get_reaction_counts,
    get_session_snapshot,
    save_reaction,
    save_session,
)
from namengine.core.schemas import NameResult, NamingBrief


class ResultsMobileStabilizationTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "results-mobile.sqlite3")
        self.previous_db_path = os.environ.get("NAMENGINE_DB_PATH")
        self.previous_api_key = os.environ.get("OPENAI_API_KEY")
        os.environ["NAMENGINE_DB_PATH"] = self.db_path
        os.environ.pop("OPENAI_API_KEY", None)
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        if self.previous_db_path is None:
            os.environ.pop("NAMENGINE_DB_PATH", None)
        else:
            os.environ["NAMENGINE_DB_PATH"] = self.previous_db_path
        if self.previous_api_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self.previous_api_key
        self.tempdir.cleanup()

    def _seed_results(self, session_id="pet-mobile-results"):
        brief = NamingBrief(vertical="pet", inputs={"pet_type": "Dog", "style": "Warm"})
        results = [
            NameResult(
                id="pet-1",
                name="Luna",
                slug="luna",
                pronunciation="LOO-nah",
                meaning="Bright moon",
                origin="Latin",
                tagline="Warm, bright, and easy to call.",
                why_this_name="It matches a warm, affectionate direction.",
                fit_note="Best for a gentle companion.",
                risks=["Popular in some pet communities."],
                tags=["callable", "warm", "pet-ready"],
            ),
            NameResult(
                id="pet-2",
                name="Pippin",
                slug="pippin",
                pronunciation="PIP-in",
                meaning="Unknown",
                tagline="Playful without feeling flimsy.",
                why_this_name="It matches an upbeat personality.",
                fit_note="Best for an energetic companion.",
                risks=[],
            ),
        ]
        save_session(session_id, "pet", brief, results)
        return session_id

    def test_public_results_show_only_love_and_no_for_all_launch_verticals(self):
        routes = (
            "/baby/results?gender=Girl&style=Classic&sound=Soft",
            "/pet/results?pet_type=Dog&style=Classic&vibe=Playful",
            "/business/results?business_description=Studio&audience=Consumers&style=Clear+and+credible",
        )
        for route in routes:
            with self.subTest(route=route):
                body = self.client.get(route).get_data(as_text=True)
                self.assertIn('data-reaction-value="love"', body)
                self.assertIn('data-reaction-value="no"', body)
                self.assertNotIn('data-reaction-value="maybe"', body)
                self.assertNotIn("images/reactions/maybe.jpg", body)
                if route.startswith("/baby"):
                    self.assertIn("Love it", body)
                    self.assertIn("Not for us", body)
                else:
                    self.assertIn("Love or No reactions", body)

    def test_mobile_card_markup_keeps_summary_controls_and_full_detail(self):
        session_id = self._seed_results()
        body = self.client.get(f"/results/session/{session_id}").get_data(as_text=True)

        self.assertEqual(body.count("data-result-card>"), 2)
        self.assertEqual(body.count('class="result-card-toggle"'), 2)
        self.assertIn('aria-expanded="false"', body)
        self.assertIn('aria-controls="result-details-1"', body)
        self.assertIn('id="result-details-1"', body)
        self.assertIn("View details", body)
        self.assertIn("Why this feels like them", body)
        self.assertIn("Best fit", body)
        self.assertIn("Worth noting", body)
        self.assertIn("Choose Luna", body)

    def test_meaning_is_shown_only_when_useful(self):
        session_id = self._seed_results()
        body = self.client.get(f"/results/session/{session_id}").get_data(as_text=True)

        self.assertIn("Meaning:</strong> Bright moon", body)
        self.assertNotIn("Meaning:</strong> Unknown", body)

    def test_combined_origin_text_requires_an_explicit_meaning_label(self):
        explicit = {
            "meaning": "",
            "metadata": {"origin_meaning": "Latin origin; Meaning: bright moon | traditional use"},
        }
        generic = {
            "meaning": "",
            "metadata": {"origin_meaning": "Latin-rooted and often associated with moonlight."},
        }

        self.assertEqual(collapsed_result_meaning(explicit), "bright moon")
        self.assertEqual(collapsed_result_meaning(generic), "")
        self.assertEqual(
            collapsed_result_meaning(
                {"meaning": "A baby name shaped for sound, warmth, and family fit."}
            ),
            "",
        )

    def test_reaction_state_persists_and_maybe_is_rejected_publicly(self):
        session_id = self._seed_results()
        accepted = self.client.post(
            "/api/react",
            json={"session_id": session_id, "result_id": "pet-1", "value": "love"},
        )
        rejected = self.client.post(
            "/api/react",
            json={"session_id": session_id, "result_id": "pet-2", "value": "maybe"},
        )
        body = self.client.get(f"/results/session/{session_id}").get_data(as_text=True)

        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(rejected.status_code, 400)
        self.assertIn('class="is-selected" data-reaction-value="love"', body)
        self.assertIn('aria-pressed="true"', body)

    def test_historical_maybe_remains_readable_without_public_display(self):
        session_id = self._seed_results()
        save_reaction(build_reaction(session_id, "pet-2", "maybe"))

        snapshot = get_session_snapshot(session_id)
        body = self.client.get(f"/results/session/{session_id}").get_data(as_text=True)

        self.assertEqual(get_reaction_counts(session_id)["maybe"], 1)
        self.assertEqual(snapshot["reactions"][0]["value"], "maybe")
        self.assertNotIn('data-reaction-value="maybe"', body)
        self.assertNotIn("Maybe 1", body)

    def test_empty_reactions_return_a_helpful_refinement_gate(self):
        session_id = self._seed_results()

        response = self.client.post(
            "/refine",
            data={"session_id": session_id, "instruction": "shorter"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("React to 3 more names", response.get_data(as_text=True))

    def test_results_assets_include_progressive_mobile_accordion(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "static" / "js" / "results-accordion.js").read_text(encoding="utf-8")
        css = (root / "static" / "css" / "platform.css").read_text(encoding="utf-8")

        self.assertIn("results-accordion-ready", script)
        self.assertIn("cards.forEach", script)
        self.assertIn('setAttribute("aria-expanded"', script)
        self.assertIn(".results-accordion-ready .result-card:not(.is-expanded)", css)
        self.assertIn("@media (max-width: 760px)", css)

    def test_homepage_mobile_sections_have_final_full_width_cascade_override(self):
        root = Path(__file__).resolve().parents[1]
        css = (root / "static" / "css" / "platform.css").read_text(encoding="utf-8")
        body = self.client.get("/").get_data(as_text=True)

        legacy_two_column = css.index(
            ".home-vertical-grid {\n    grid-template-columns: repeat(2, minmax(0, 1fr));"
        )
        hotfix = css.index("/*\n * Mobile homepage hotfix.")

        self.assertGreater(hotfix, legacy_two_column)
        self.assertIn("main > .home-hero", css[hotfix:])
        self.assertIn("main > .home-verticals > .home-vertical-grid", css[hotfix:])
        self.assertIn("grid-template-columns: minmax(0, 1fr);", css[hotfix:])
        self.assertIn("20260716-homepage-shared-layout-hotfix-v1", body)
        self.assertNotIn("home-visual-panel", body)
        self.assertNotIn("home-system-panel", body)


if __name__ == "__main__":
    unittest.main()
