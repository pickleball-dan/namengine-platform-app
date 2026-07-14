import unittest

from namengine.core import (
    brief_from_fixture,
    compare_contrast_groups,
    load_taste_engine_fixtures,
    run_taste_engine_fixture_set,
    summarize_taste_engine_eval,
)


class PhaseTwentyTwoTasteEngineEvalsTest(unittest.TestCase):
    def test_fixture_library_loads_core_scenarios(self):
        fixtures = load_taste_engine_fixtures()
        fixture_ids = {fixture.id for fixture in fixtures}

        self.assertGreaterEqual(len(fixtures), 10)
        self.assertIn("baby-classic-soft-familiar", fixture_ids)
        self.assertIn("baby-rare-strong-distinctive", fixture_ids)
        self.assertIn("baby-scandinavian-minimalist", fixture_ids)
        self.assertIn("business-modern-luxury", fixture_ids)

    def test_fixture_brief_applies_feelings_scale_values(self):
        fixture = next(
            item for item in load_taste_engine_fixtures() if item.id == "baby-family-context-led"
        )
        brief = brief_from_fixture(fixture)

        self.assertEqual(brief.inputs["taste_strength_about_your_baby"], 70)
        self.assertIn("about your baby", brief.inputs["taste_focus"])
        self.assertEqual(brief.inputs["family_context"], fixture.inputs["family_context"])

    def test_fallback_eval_contrasts_major_baby_taste_lanes(self):
        fixtures = [
            fixture
            for fixture in load_taste_engine_fixtures()
            if fixture.id in {"baby-classic-soft-familiar", "baby-rare-strong-distinctive"}
        ]
        results = run_taste_engine_fixture_set(fixtures, use_ai=False)
        contrasts = compare_contrast_groups(results, max_top3_overlap=1, min_unique_difference=4)

        self.assertEqual(len(contrasts), 1)
        self.assertTrue(contrasts[0].passed, contrasts[0])

    def test_eval_summary_is_audit_friendly(self):
        fixtures = load_taste_engine_fixtures()[:3]
        results = run_taste_engine_fixture_set(fixtures, use_ai=False)
        summary = summarize_taste_engine_eval(results)

        self.assertEqual(summary["fixture_count"], 3)
        self.assertIn("fixtures", summary)
        self.assertIn("contrasts", summary)
        self.assertGreaterEqual(summary["signal_hit_count"], 3)
        self.assertIn("fallback", summary["providers"])


if __name__ == "__main__":
    unittest.main()
