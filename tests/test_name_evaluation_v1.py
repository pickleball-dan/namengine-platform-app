import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from namengine.core import build_brief, generate_names
from namengine.core.name_evaluation import (
    AcceptanceCriterion,
    DEFAULT_PACK_ROOT,
    FixtureValidationError,
    evaluate_fixture,
    evaluate_generated_fixture,
    load_evaluation_pack,
    serialize_evaluation,
    summarize_evaluation_pack,
    validate_fixture,
)
from namengine.core.schemas import NameResult
from namengine.verticals import BABY, PET


BABY_PACK = DEFAULT_PACK_ROOT / "baby"


class NameEvaluationFrameworkV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_fixture = json.loads(
            (BABY_PACK / "classic_soft_familiar_girl.json").read_text(encoding="utf-8")
        )

    def _payload(self, **changes):
        payload = json.loads(json.dumps(self.raw_fixture))
        payload.update(changes)
        return payload

    def _write(self, directory: Path, filename: str, payload) -> None:
        (directory / filename).write_text(json.dumps(payload), encoding="utf-8")

    def test_fixture_schema_validation_and_valid_baby_pack_loading(self):
        schema = json.loads((DEFAULT_PACK_ROOT / "schema.json").read_text(encoding="utf-8"))
        fixtures = load_evaluation_pack(BABY_PACK)

        self.assertEqual(schema["properties"]["schema_version"]["const"], "name-evaluation-fixture-v1")
        self.assertEqual(len(fixtures), 10)
        self.assertEqual(len({fixture.fixture_id for fixture in fixtures}), 10)
        self.assertTrue(all(fixture.vertical == "baby" for fixture in fixtures))
        self.assertTrue(all(fixture.criteria for fixture in fixtures))

    def test_duplicate_ids_and_malformed_fixtures_are_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            self._write(root, "one.json", self._payload())
            self._write(root, "two.json", self._payload())
            with self.assertRaisesRegex(FixtureValidationError, "Duplicate fixture ID"):
                load_evaluation_pack(root)

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            (root / "broken.json").write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(FixtureValidationError, "Malformed fixture"):
                load_evaluation_pack(root)

        with self.assertRaisesRegex(FixtureValidationError, "missing fields"):
            validate_fixture({"fixture_id": "incomplete"})

    def test_invalid_vertical_weight_and_unknown_criterion_are_rejected(self):
        with self.assertRaisesRegex(FixtureValidationError, "invalid vertical"):
            validate_fixture(self._payload(vertical="place"))

        invalid_weight = self._payload()
        invalid_weight["acceptance_criteria"]["criteria"][0]["weight"] = float("nan")
        with self.assertRaisesRegex(FixtureValidationError, "finite number"):
            validate_fixture(invalid_weight)

        unknown = self._payload()
        unknown["acceptance_criteria"]["criteria"][0]["criterion"] = "baby_magic"
        with self.assertRaisesRegex(FixtureValidationError, "unknown criterion"):
            validate_fixture(unknown)

    def test_disabled_vertical_and_tag_filters(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            disabled = self._payload(fixture_id="disabled", enabled=False, tags=["disabled-tag"])
            enabled = self._payload(fixture_id="enabled", tags=["enabled-tag"])
            self._write(root, "disabled.json", disabled)
            self._write(root, "enabled.json", enabled)

            self.assertEqual([item.fixture_id for item in load_evaluation_pack(root)], ["enabled"])
            self.assertEqual(len(load_evaluation_pack(root, include_disabled=True)), 2)
            self.assertEqual(
                [item.fixture_id for item in load_evaluation_pack(root, tags={"disabled-tag"}, include_disabled=True)],
                ["disabled"],
            )
            self.assertEqual(load_evaluation_pack(root, vertical="pet"), [])

    def test_criterion_pass_fail_and_not_applicable_results(self):
        base = validate_fixture(self._payload())
        fixture = replace(
            base,
            minimum_normalized_score=0.0,
            rejection_candidates=("Nevaeh",),
            criteria=(
                AcceptanceCriterion("duplicate_prevention", 1.0),
                AcceptanceCriterion("prohibited_names", 1.0),
                AcceptanceCriterion("deterministic_ordering", 1.0, required=False),
            ),
        )
        result = evaluate_fixture(
            fixture,
            [NameResult(id="one", name="Nevaeh", slug="nevaeh")],
        )

        self.assertEqual(
            [item.status for item in result.criterion_results],
            ["pass", "fail", "not_applicable"],
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.maximum_score, 2.0)

    def test_aggregate_scoring_and_deterministic_serialization(self):
        fixture = validate_fixture(self._payload())
        result = evaluate_generated_fixture(fixture)
        summary = summarize_evaluation_pack([result])

        self.assertEqual(summary.fixture_count, 1)
        self.assertEqual(summary.passed_count + summary.failed_count, 1)
        self.assertGreater(summary.maximum_score, 0)
        self.assertEqual(serialize_evaluation(summary), serialize_evaluation(summary))
        decoded = json.loads(serialize_evaluation(summary))
        self.assertEqual(decoded["results"][0]["fixture_id"], fixture.fixture_id)

    def test_baby_fixture_evaluation_uses_baby_pack_adapter(self):
        fixture = next(
            item
            for item in load_evaluation_pack(BABY_PACK)
            if item.fixture_id == "baby-eval-chinese-gender-behavior"
        )
        result = evaluate_generated_fixture(fixture)

        self.assertEqual(result.adapter_version, "baby-evaluation-pack-v1")
        self.assertEqual(result.vertical, "baby")
        self.assertTrue(result.evaluated_candidates)
        self.assertIn("gender_fit", {item.criterion for item in result.criterion_results})
        self.assertTrue(0 <= result.normalized_score <= 1)

    def test_complete_baby_pack_evaluates_and_aggregates(self):
        results = [evaluate_generated_fixture(fixture) for fixture in load_evaluation_pack(BABY_PACK)]
        summary = summarize_evaluation_pack(results)

        self.assertEqual(summary.fixture_count, 10)
        self.assertEqual(summary.passed_count + summary.failed_count, 10)
        self.assertEqual(
            [item.fixture_id for item in summary.results],
            sorted(item.fixture_id for item in results),
        )

    def test_privacy_criterion_reports_paths_without_echoing_secrets(self):
        base = validate_fixture(self._payload())
        fixture = replace(
            base,
            minimum_normalized_score=0.0,
            criteria=(AcceptanceCriterion("privacy_safety", 1.0),),
        )
        candidate = NameResult(
            id="unsafe",
            name="Clara",
            slug="clara",
            metadata={"api_key": "sk-this-must-never-be-rendered"},
        )
        result = evaluate_fixture(fixture, [candidate])
        serialized = serialize_evaluation(result)

        self.assertFalse(result.passed)
        self.assertNotIn("sk-this-must-never-be-rendered", serialized)
        self.assertIn("candidate[0].metadata.api_key", serialized)

    def test_pet_generation_order_and_metadata_remain_legacy(self):
        brief = build_brief(PET, {"style": "Warm", "pet_type": "Dog", "vibe": "Gentle"})
        first = generate_names(PET, brief, use_ai=False)
        second = generate_names(PET, brief, use_ai=False)

        expected = ["Rosie", "Juniper", "Ollie", "Remy", "Lottie", "Theo", "Maple", "Clover"]
        self.assertEqual([item.name for item in first], expected)
        self.assertEqual([item.name for item in second], expected)
        self.assertNotIn("quality_score_version", first[0].metadata)


if __name__ == "__main__":
    unittest.main()
