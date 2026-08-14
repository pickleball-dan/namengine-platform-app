import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import simulate_generation_quality as simulator


class GenerationQualitySimulatorTest(unittest.TestCase):
    def test_fixture_verticals_are_registered_and_future_friendly(self):
        scenarios = simulator.load_scenarios()

        self.assertGreaterEqual(len(scenarios), 3)
        self.assertTrue({"baby", "pet", "business"}.issubset({scenario.vertical for scenario in scenarios}))
        for scenario in scenarios:
            with self.subTest(scenario=scenario.id):
                self.assertIn(scenario.vertical, simulator.VERTICALS)
                self.assertTrue(scenario.inputs)
                self.assertGreaterEqual(scenario.rounds, 1)
                self.assertTrue(scenario.expected_signals)

    def test_fast_selection_uses_only_fast_active_vertical_scenarios(self):
        args = simulator.parse_args_from(["--fast"]) if hasattr(simulator, "parse_args_from") else None
        if args is None:
            with patch.object(simulator.sys, "argv", ["simulate_generation_quality.py", "--fast"]):
                args = simulator.parse_args()
        selected = simulator.select_scenarios(simulator.load_scenarios(), args)

        self.assertEqual({scenario.mode for scenario in selected}, {"fast"})
        self.assertEqual({scenario.vertical for scenario in selected}, {"baby", "pet", "business"})

    def test_detect_anomalies_catches_structural_failures(self):
        scenario = simulator.GenerationScenario(
            id="unit",
            label="Unit",
            vertical="baby",
            inputs={"gender": "Girl"},
            expected_count=2,
            avoid_names=["Olivia"],
        )
        from namengine.core.schemas import NameResult

        anomalies = simulator.detect_anomalies(
            scenario,
            [
                NameResult(id="1", name="Olivia", slug="olivia"),
                NameResult(id="2", name="Olivia", slug="olivia-2", metadata={"legacy": "maybe"}),
            ],
            expected_count=3,
        )

        codes = {item["code"] for item in anomalies}
        self.assertIn("too_few_results", codes)
        self.assertIn("duplicate_names", codes)
        self.assertIn("avoid_name_used", codes)
        self.assertIn("legacy_maybe_signal", codes)

    def test_fast_run_writes_mission_control_ready_summary_shape(self):
        scenarios = [scenario for scenario in simulator.load_scenarios() if scenario.mode == "fast"]
        results = [simulator.run_scenario(scenario, use_ai=False) for scenario in scenarios]
        summary = simulator.summarize_run(results, run_id="generation-qa-test", use_ai=False)

        self.assertEqual(summary["schema_version"], simulator.SIMULATOR_SCHEMA_VERSION)
        self.assertEqual(summary["scenario_count"], 3)
        self.assertIn("anomalies", summary)
        self.assertIn("scenarios", summary)
        self.assertEqual({scenario["vertical"] for scenario in summary["scenarios"]}, {"baby", "pet", "business"})

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = simulator.write_artifacts(results, summary, Path(tmp))
            self.assertTrue((run_dir / "summary.json").exists())
            self.assertTrue((run_dir / "report.md").exists())
            self.assertTrue((run_dir / "results.json").exists())
            latest_summary = Path(tmp) / "latest" / "summary.json"
            self.assertTrue(latest_summary.exists())
            loaded = json.loads(latest_summary.read_text(encoding="utf-8"))
            self.assertEqual(loaded["run_id"], "generation-qa-test")


if __name__ == "__main__":
    unittest.main()
