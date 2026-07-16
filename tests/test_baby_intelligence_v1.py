import json
import math
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from namengine.core.baby_intelligence import (
    BabyIntelligenceConfig,
    analyze_baby_candidate_diversity,
    analyze_baby_weaknesses,
    run_baby_intelligence,
)
from namengine.core.generation import generate_names
from namengine.core.intelligence_baselines import (
    compare_with_baby_intelligence_baseline,
    create_baby_intelligence_baseline,
    load_baby_intelligence_baseline,
    save_baby_intelligence_baseline,
)
from namengine.core.intelligence_comparison import compare_baby_intelligence_runs
from namengine.core.intelligence_runs import DiversityAnalysis
from namengine.core.name_evaluation import DEFAULT_PACK_ROOT
from namengine.core.schemas import NameResult


BABY_PACK = DEFAULT_PACK_ROOT / "baby"
CLASSIC_FIXTURE = "baby-eval-classic-soft-familiar-girl"
RARE_FIXTURE = "baby-eval-rare-strong-distinctive-boy"


def deterministic_generator(vertical, brief, config):
    return generate_names(vertical, brief, use_ai=False)


class BabyIntelligenceV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classic_run = run_baby_intelligence(
            BabyIntelligenceConfig(fixture_ids=(CLASSIC_FIXTURE,)),
            generation_callable=deterministic_generator,
        )

    def test_full_pack_runner_and_version_metadata(self):
        run = run_baby_intelligence(generation_callable=deterministic_generator)

        self.assertEqual(len(run.fixture_ids), 10)
        self.assertEqual(len(run.fixture_results), 10)
        self.assertEqual(run.vertical, "baby")
        self.assertEqual(run.prompt_version, "namengine-baby-quality-v1")
        self.assertEqual(run.intake_schema_version, "baby-intake-v1")
        self.assertEqual(run.canonical_intent_version, "canonical-naming-intent-v1")
        self.assertEqual(run.quality_adapter_version, "baby-quality-score-v1")
        self.assertEqual(run.evaluation_adapter_version, "baby-evaluation-pack-v1")
        self.assertTrue(0 <= run.normalized_score <= 1)
        self.assertEqual(json.loads(run.serialize())["run_id"], run.run_id)
        audit = run.audit_metadata()
        self.assertEqual(audit["baby_intelligence_run_id"], run.run_id)
        self.assertNotIn("candidates", audit)
        self.assertNotIn("intake", audit)

    def test_fixture_and_tag_filtering_repeat_and_seed_diagnostic(self):
        fixture_run = run_baby_intelligence(
            BabyIntelligenceConfig(
                fixture_ids=(CLASSIC_FIXTURE,), repeat_count=2, deterministic_seed=42
            ),
            generation_callable=deterministic_generator,
        )
        tag_run = run_baby_intelligence(
            BabyIntelligenceConfig(tags=("chinese",)),
            generation_callable=deterministic_generator,
        )

        self.assertEqual(len(fixture_run.fixture_results), 2)
        self.assertEqual([item.repeat_index for item in fixture_run.fixture_results], [1, 2])
        self.assertIn("seed", fixture_run.diagnostics[0].lower())
        self.assertEqual(tag_run.fixture_ids, ("baby-eval-chinese-gender-behavior",))
        with self.assertRaisesRegex(ValueError, "Unknown or disabled"):
            run_baby_intelligence(BabyIntelligenceConfig(fixture_ids=("missing",)))
        with self.assertRaisesRegex(ValueError, "Unknown Baby prompt"):
            run_baby_intelligence(BabyIntelligenceConfig(prompt_version="unknown-prompt"))
        with self.assertRaisesRegex(ValueError, "Fallback provider cannot"):
            BabyIntelligenceConfig(provider="fallback", include_fallback=False)

    def test_disabled_fixtures_are_not_executed(self):
        raw = json.loads((BABY_PACK / "classic_soft_familiar_girl.json").read_text(encoding="utf-8"))
        raw["enabled"] = False
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "disabled.json").write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "selected no enabled"):
                run_baby_intelligence(pack_path=root)

    def test_timeout_and_generation_failure_are_sanitized(self):
        def timeout(*args):
            raise TimeoutError("provider internal timeout detail")

        def failure(*args):
            raise RuntimeError("sk-secret traceback customer payload")

        timeout_run = run_baby_intelligence(
            BabyIntelligenceConfig(fixture_ids=(CLASSIC_FIXTURE,)), generation_callable=timeout
        )
        failed_run = run_baby_intelligence(
            BabyIntelligenceConfig(fixture_ids=(CLASSIC_FIXTURE,)), generation_callable=failure
        )

        self.assertTrue(timeout_run.fixture_results[0].timeout)
        self.assertEqual(timeout_run.regression_status, "execution_failure")
        serialized = failed_run.serialize()
        self.assertNotIn("sk-secret", serialized)
        self.assertNotIn("traceback customer payload", serialized)
        self.assertEqual(failed_run.fixture_results[0].execution_error, "generation_RuntimeError")

    def test_fallback_and_candidate_diagnostics(self):
        result = self.classic_run.fixture_results[0]

        self.assertTrue(result.fallback_used)
        self.assertTrue(result.candidates)
        first = result.candidates[0]
        self.assertEqual(first.final_rank, 1)
        self.assertIsNotNone(first.shared_quality_score)
        self.assertTrue(first.baby_quality_dimensions)
        self.assertTrue(first.tie_break_fields)
        self.assertNotIn("prompt", json.dumps(first.baby_quality_dimensions))

    def test_run_serialization_is_deterministic_bounded_and_finite(self):
        self.assertEqual(self.classic_run.serialize(), self.classic_run.serialize())
        serialized = self.classic_run.serialize()
        self.assertNotIn("raw_intake", serialized)
        self.assertNotIn("canonical_intent\"", serialized)
        with self.assertRaises(ValueError):
            replace(self.classic_run, normalized_score=math.nan)
        with self.assertRaises(ValueError):
            replace(self.classic_run, aggregate_score=-1)
        bounded = replace(self.classic_run, diagnostics=("x" * 1000,))
        self.assertNotIn("x" * 501, bounded.serialize())

        metrics = {item.code: item for item in self.classic_run.fixture_results[0].metrics}
        self.assertEqual(metrics["professional_usability"].status, "not_applicable")
        self.assertEqual(metrics["honor_name_influence"].status, "not_applicable")

    def test_baseline_create_save_load_and_compare(self):
        baseline = create_baby_intelligence_baseline(
            self.classic_run, created_at="2026-01-01T00:00:00+00:00"
        )
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "baseline.json"
            save_baby_intelligence_baseline(baseline, path)
            loaded = load_baby_intelligence_baseline(path)

        self.assertEqual(loaded.serialize(), baseline.serialize())
        comparison = compare_with_baby_intelligence_baseline(loaded, self.classic_run)
        self.assertTrue(comparison.compatible)
        self.assertEqual(comparison.verdict, "pass")

    def test_corrupt_and_private_baselines_are_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "baseline.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "corrupt"):
                load_baby_intelligence_baseline(path)
            payload = create_baby_intelligence_baseline(self.classic_run).to_dict()
            payload["raw_intake"] = {"notes": "private"}
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid structure"):
                load_baby_intelligence_baseline(path)

    def test_checked_in_baseline_is_synthetic_and_loadable(self):
        baseline_path = Path("tests/fixtures/baby_intelligence/baseline_v1.json")
        baseline = load_baby_intelligence_baseline(baseline_path)
        serialized = baseline.serialize()

        self.assertEqual(len(baseline.run.fixture_ids), 10)
        self.assertIn("Chinese heritage fallback", serialized)
        self.assertNotIn("raw_intake", serialized)
        self.assertNotIn("customer_intake", serialized)
        self.assertNotIn("hidden_prompt", serialized)

    def test_comparison_improvement_regression_and_threshold(self):
        fixture = self.classic_run.fixture_results[0]
        lower_score = max(0.0, self.classic_run.normalized_score - 0.1)
        lower_fixture = replace(
            fixture, normalized_score=max(0.0, fixture.normalized_score - 0.1)
        )
        lower_baseline = replace(
            self.classic_run,
            run_id="lower-baseline",
            fixture_results=(lower_fixture,),
            normalized_score=lower_score,
        )
        comparison = compare_baby_intelligence_runs(lower_baseline, self.classic_run)
        self.assertTrue(any(item.metric == "aggregate_normalized_score" for item in comparison.improved_metrics))

        tiny = replace(self.classic_run, run_id="tiny", normalized_score=max(0, self.classic_run.normalized_score - 0.005))
        tolerant = compare_baby_intelligence_runs(self.classic_run, tiny)
        self.assertIn("aggregate_normalized_score", {item.metric for item in tolerant.unchanged_metrics})

        failing_fixture = replace(fixture, passed=False, normalized_score=0.0, failure_reasons=("failed",))
        failing = replace(
            self.classic_run, run_id="failing", fixture_results=(failing_fixture,),
            normalized_score=0.0, pass_rate=0.0, failure_count=1,
        )
        regression = compare_baby_intelligence_runs(self.classic_run, failing)
        if fixture.passed:
            self.assertIn(f"{CLASSIC_FIXTURE}#1", regression.newly_failing_fixtures)
            self.assertEqual(regression.verdict, "regression_detected")

        lower_passing = replace(failing, run_id="lower-passing", fixture_results=(failing_fixture,))
        newly_passing = compare_baby_intelligence_runs(lower_passing, self.classic_run)
        if fixture.passed:
            self.assertIn(f"{CLASSIC_FIXTURE}#1", newly_passing.newly_passing_fixtures)

        no_fallback_fixture = replace(fixture, fallback_used=False)
        no_fallback = replace(self.classic_run, run_id="no-fallback", fixture_results=(no_fallback_fixture,))
        fallback_regression = compare_baby_intelligence_runs(no_fallback, self.classic_run)
        self.assertIn("fallback_rate", {item.metric for item in fallback_regression.regressed_metrics})

    def test_incompatible_comparison_and_stable_serialization(self):
        incompatible = replace(self.classic_run, run_id="other", prompt_version="future-prompt")
        comparison = compare_baby_intelligence_runs(self.classic_run, incompatible)

        # Prompt changes are reported in deltas but do not make fixture evidence structurally incompatible.
        self.assertTrue(comparison.compatible)
        other_provider = replace(self.classic_run, run_id="provider", provider="openai")
        cross_version = compare_baby_intelligence_runs(self.classic_run, other_provider)
        self.assertTrue(cross_version.compatible)
        self.assertTrue(cross_version.compatibility_warnings)
        baseline = create_baby_intelligence_baseline(self.classic_run)
        incompatible_provider = compare_with_baby_intelligence_baseline(baseline, other_provider)
        self.assertFalse(incompatible_provider.compatible)
        self.assertEqual(incompatible_provider.verdict, "incompatible_comparison")
        self.assertEqual(incompatible_provider.serialize(), incompatible_provider.serialize())

    def test_critical_privacy_regression(self):
        fixture = self.classic_run.fixture_results[0]
        criteria = []
        found = False
        for criterion in fixture.criterion_results:
            row = dict(criterion)
            if row["criterion"] == "privacy_safety":
                row.update(status="fail", score=0.0)
                found = True
            criteria.append(row)
        self.assertTrue(found)
        current_fixture = replace(fixture, criterion_results=tuple(criteria))
        current = replace(self.classic_run, run_id="privacy-regression", fixture_results=(current_fixture,))
        comparison = compare_baby_intelligence_runs(self.classic_run, current)

        self.assertIn("critical", {item.severity for item in comparison.regressions})
        self.assertEqual(comparison.verdict, "regression_detected")

    def test_critical_privacy_failure_fails_the_run_without_leaking_value(self):
        def unsafe(vertical, brief, config):
            results = generate_names(vertical, brief, use_ai=False)
            results[0].metadata["api_key"] = "sk-do-not-persist"
            return results

        run = run_baby_intelligence(
            BabyIntelligenceConfig(fixture_ids=(CLASSIC_FIXTURE,)),
            generation_callable=unsafe,
        )

        self.assertEqual(run.regression_status, "regression_detected")
        self.assertNotIn("sk-do-not-persist", run.serialize())
        self.assertIn("privacy_safety", {item.code for item in run.weaknesses})

    def test_diversity_duplicates_variants_concentration_and_healthy_list(self):
        duplicate = [
            NameResult(id="1", name="Maya", slug="maya"),
            NameResult(id="2", name="Maya", slug="maya-2"),
            NameResult(id="3", name="Maia", slug="maia"),
            NameResult(id="4", name="Mara", slug="mara"),
            NameResult(id="5", name="Anne-Marie", slug="anne-marie"),
            NameResult(id="6", name="Anne Marie", slug="anne-marie-2"),
        ]
        analysis = analyze_baby_candidate_diversity(duplicate)
        self.assertIn("maya", analysis.exact_duplicates)
        self.assertIn("annemarie", analysis.normalized_duplicates)
        self.assertTrue(analysis.near_duplicate_pairs)
        self.assertGreater(analysis.first_letter_concentration, 0.5)
        self.assertTrue(analysis.repeated_roots or analysis.repeated_endings)

        healthy = [
            NameResult(id=str(index), name=name, slug=name.lower(), origin=origin, tags=[tag])
            for index, (name, origin, tag) in enumerate(
                [("Clara", "Latin", "classic"), ("Juniper", "English", "nature"),
                 ("Noemi", "Hebrew", "global"), ("Maeve", "Irish", "strong"),
                 ("Iris", "Greek", "vintage"), ("Zara", "Arabic", "modern")], 1
            )
        ]
        healthy_analysis = analyze_baby_candidate_diversity(healthy)
        self.assertGreaterEqual(healthy_analysis.score, 0.8)
        self.assertEqual(analyze_baby_candidate_diversity(healthy[:1]).status, "not_applicable")

    def test_weakness_classification_for_culture_gender_fallback_and_explanations(self):
        fixture = self.classic_run.fixture_results[0]
        criteria = tuple(
            {
                "criterion": criterion,
                "status": "fail",
                "score": 0.0,
                "maximum_score": 1.0,
                "required": True,
                "reason": "bounded",
                "details": {},
            }
            for criterion in ("cultural_relevance", "gender_fit", "explanation_completeness")
        )
        weak = replace(
            fixture,
            criterion_results=criteria,
            fallback_used=True,
            diversity=DiversityAnalysis("applicable", 0.2, reasons=("concentrated",)),
        )
        weaknesses = analyze_baby_weaknesses((weak,))
        by_code = {item.code: item for item in weaknesses}

        self.assertEqual(by_code["low_cultural_relevance"].likely_subsystem, "candidate generation")
        self.assertEqual(by_code["low_gender_fit"].likely_subsystem, "candidate generation")
        self.assertEqual(by_code["weak_explanations"].likely_subsystem, "quality adapter")
        self.assertEqual(by_code["fallback_dependence"].likely_subsystem, "fallback behavior")
        self.assertEqual(by_code["candidate_diversity"].likely_subsystem, "post-processing")
        self.assertTrue(all(len(item.explanation) <= 500 for item in weaknesses))

    def test_current_pack_and_production_generation_are_unchanged(self):
        before = deterministic_generator
        run = run_baby_intelligence(
            BabyIntelligenceConfig(fixture_ids=(RARE_FIXTURE,)), generation_callable=before
        )

        self.assertEqual(run.fixture_ids, (RARE_FIXTURE,))
        self.assertNotIn("intelligence_run_id", run.fixture_results[0].candidates[0].baby_quality_dimensions)


if __name__ == "__main__":
    unittest.main()
