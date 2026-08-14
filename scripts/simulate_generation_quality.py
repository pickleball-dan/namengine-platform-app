"""Run local NamEngine generation-quality simulations.

This is a local QA harness for realistic user-input scenarios. By default it
uses fallback/local generation only; live AI requires the explicit --use-ai flag.

Examples:
    python scripts/simulate_generation_quality.py --fast
    python scripts/simulate_generation_quality.py --full
    python scripts/simulate_generation_quality.py --vertical baby --use-ai
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from namengine.core.briefs import build_brief
from namengine.core.generation import generate_names
from namengine.core.schemas import NameResult, to_plain_data
from namengine.verticals import VERTICALS, get_vertical

DEFAULT_SCENARIO_PATH = REPO_ROOT / "tests" / "fixtures" / "generation_scenarios.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "qa-artifacts" / "generation-runs"
ACTIVE_VERTICALS = {"baby", "pet", "business"}
SIMULATOR_SCHEMA_VERSION = "generation-simulator-v1"


@dataclass(slots=True)
class GenerationScenario:
    id: str
    label: str
    vertical: str
    inputs: dict[str, Any]
    mode: str = "full"
    rounds: int = 1
    expected_count: int | None = None
    expected_signals: list[str] = field(default_factory=list)
    avoid_names: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ScenarioRoundResult:
    round_number: int
    passed: bool
    latency_ms: int
    provider: str
    pipeline: str
    model: str
    names: list[str]
    anomalies: list[dict[str, str]]
    results: list[dict[str, Any]]


@dataclass(slots=True)
class ScenarioRunResult:
    id: str
    label: str
    vertical: str
    passed: bool
    expected_signals: list[str]
    signal_hits: list[str]
    anomaly_count: int
    rounds: list[ScenarioRoundResult]
    inputs: dict[str, Any]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NamEngine generation quality simulations.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fast", action="store_true", help="Run only scenarios marked mode=fast.")
    mode.add_argument("--full", action="store_true", help="Run all scenarios in the fixture file.")
    parser.add_argument("--scenario-file", default=str(DEFAULT_SCENARIO_PATH), help="Scenario fixture JSON path.")
    parser.add_argument("--scenario", action="append", default=[], help="Scenario id to include. Repeatable.")
    parser.add_argument("--vertical", action="append", default=[], help="Vertical slug to include. Repeatable.")
    parser.add_argument(
        "--include-under-development",
        action="store_true",
        help="Allow fixture verticals outside the current active launch set.",
    )
    parser.add_argument("--rounds", type=int, default=0, help="Override rounds for every selected scenario.")
    parser.add_argument("--use-ai", action="store_true", help="Use live AI generation when configured. Off by default.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_ROOT), help="Root directory for generated reports.")
    parser.add_argument("--no-write", action="store_true", help="Print summary only; do not write artifacts.")
    return parser.parse_args(argv)


def load_scenarios(path: Path | str = DEFAULT_SCENARIO_PATH) -> list[GenerationScenario]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    scenarios: list[GenerationScenario] = []
    for row in payload:
        scenarios.append(
            GenerationScenario(
                id=str(row["id"]),
                label=str(row.get("label") or row["id"]),
                vertical=str(row["vertical"]),
                inputs=dict(row.get("inputs", {})),
                mode=str(row.get("mode") or "full"),
                rounds=max(1, int(row.get("rounds", 1))),
                expected_count=int(row["expected_count"]) if row.get("expected_count") is not None else None,
                expected_signals=[str(item) for item in row.get("expected_signals", [])],
                avoid_names=[str(item) for item in row.get("avoid_names", [])],
            )
        )
    return scenarios


def select_scenarios(scenarios: list[GenerationScenario], args: argparse.Namespace) -> list[GenerationScenario]:
    selected = scenarios
    if args.fast:
        selected = [scenario for scenario in selected if scenario.mode == "fast"]
    if args.scenario:
        wanted = set(args.scenario)
        selected = [scenario for scenario in selected if scenario.id in wanted]
        missing = sorted(wanted - {scenario.id for scenario in selected})
        if missing:
            raise SystemExit(f"Unknown scenario id(s): {', '.join(missing)}")
    if args.vertical:
        wanted_verticals = set(args.vertical)
        selected = [scenario for scenario in selected if scenario.vertical in wanted_verticals]
    if not args.include_under_development:
        selected = [scenario for scenario in selected if scenario.vertical in ACTIVE_VERTICALS]
    unknown_verticals = sorted({scenario.vertical for scenario in selected if scenario.vertical not in VERTICALS})
    if unknown_verticals:
        raise SystemExit(f"Unknown vertical slug(s): {', '.join(unknown_verticals)}")
    if not selected:
        raise SystemExit("No generation scenarios selected.")
    return selected


def run_scenario(scenario: GenerationScenario, *, use_ai: bool = False, rounds_override: int = 0) -> ScenarioRunResult:
    vertical = get_vertical(scenario.vertical)
    brief = build_brief(vertical, scenario.inputs)
    round_count = rounds_override if rounds_override > 0 else scenario.rounds
    previous_names: list[str] = []
    rounds: list[ScenarioRoundResult] = []
    output_text: list[str] = []

    for round_number in range(1, round_count + 1):
        start = time.perf_counter()
        try:
            results = generate_names(
                vertical,
                brief,
                round_number=round_number,
                previous_names=previous_names,
                use_ai=use_ai,
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            names = [result.name for result in results]
            previous_names.extend(names)
            output_text.extend(_result_text(result) for result in results)
            anomalies = detect_anomalies(scenario, results, expected_count=scenario.expected_count or vertical.default_result_count)
            metadata = results[0].metadata if results else {}
            provider = str(metadata.get("provider") or metadata.get("source") or "unknown")
            pipeline = str(metadata.get("engine_pipeline") or "fallback")
            model = str(metadata.get("model") or "fallback")
            serialized = [to_plain_data(result) for result in results]
        except Exception as exc:  # pragma: no cover - production-safety reporting path
            latency_ms = int((time.perf_counter() - start) * 1000)
            names = []
            anomalies = [{"code": "generation_error", "severity": "critical", "message": f"{type(exc).__name__}: {exc}"}]
            provider = "error"
            pipeline = "error"
            model = "error"
            serialized = []

        rounds.append(
            ScenarioRoundResult(
                round_number=round_number,
                passed=not any(item["severity"] in {"critical", "major"} for item in anomalies),
                latency_ms=latency_ms,
                provider=provider,
                pipeline=pipeline,
                model=model,
                names=names,
                anomalies=anomalies,
                results=serialized,
            )
        )

    signal_hits = signal_hits_for(scenario.expected_signals, "\n".join(output_text))
    scenario_anomalies = [item for round_result in rounds for item in round_result.anomalies]
    return ScenarioRunResult(
        id=scenario.id,
        label=scenario.label,
        vertical=scenario.vertical,
        passed=all(round_result.passed for round_result in rounds),
        expected_signals=scenario.expected_signals,
        signal_hits=signal_hits,
        anomaly_count=len(scenario_anomalies),
        rounds=rounds,
        inputs=scenario.inputs,
    )


def detect_anomalies(
    scenario: GenerationScenario,
    results: list[NameResult],
    *,
    expected_count: int,
) -> list[dict[str, str]]:
    anomalies: list[dict[str, str]] = []
    names = [result.name.strip() for result in results]
    normalized = [_normalize_name(name) for name in names if name.strip()]
    if len(results) < expected_count:
        anomalies.append(
            {
                "code": "too_few_results",
                "severity": "major",
                "message": f"Expected at least {expected_count} names, got {len(results)}.",
            }
        )
    if any(not name for name in names):
        anomalies.append({"code": "empty_name", "severity": "critical", "message": "At least one result has an empty name."})
    duplicates = sorted({name for name in normalized if normalized.count(name) > 1})
    if duplicates:
        anomalies.append(
            {
                "code": "duplicate_names",
                "severity": "major",
                "message": f"Duplicate normalized names: {', '.join(duplicates)}.",
            }
        )
    avoided = sorted(
        avoid for avoid in scenario.avoid_names if _normalize_name(avoid) in set(normalized)
    )
    if avoided:
        anomalies.append(
            {
                "code": "avoid_name_used",
                "severity": "major",
                "message": f"Avoid-list name appeared: {', '.join(avoided)}.",
            }
        )
    malformed = [name for name in names if len(name) > 48 or re.search(r"[{}<>]", name)]
    if malformed:
        anomalies.append(
            {
                "code": "malformed_name",
                "severity": "major",
                "message": f"Suspicious name formatting: {', '.join(malformed[:5])}.",
            }
        )
    maybe_hits = []
    for result in results:
        result_payload = json.dumps(to_plain_data(result), ensure_ascii=False).lower()
        if '"maybe"' in result_payload or " maybe " in f" {result_payload} ":
            maybe_hits.append(result.name)
    if maybe_hits:
        anomalies.append(
            {
                "code": "legacy_maybe_signal",
                "severity": "minor",
                "message": f"Legacy maybe signal found in result payload: {', '.join(maybe_hits[:5])}.",
            }
        )
    return anomalies


def signal_hits_for(expected_signals: list[str], text: str) -> list[str]:
    haystack = text.lower()
    return [signal for signal in expected_signals if signal.lower() in haystack]


def summarize_run(results: list[ScenarioRunResult], *, run_id: str, use_ai: bool) -> dict[str, Any]:
    all_rounds = [round_result for result in results for round_result in result.rounds]
    anomalies = [
        {"scenario_id": result.id, "vertical": result.vertical, "round": round_result.round_number, **anomaly}
        for result in results
        for round_result in result.rounds
        for anomaly in round_result.anomalies
    ]
    return {
        "schema_version": SIMULATOR_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "ai" if use_ai else "fallback",
        "scenario_count": len(results),
        "round_count": len(all_rounds),
        "passed_count": sum(1 for result in results if result.passed),
        "failed_count": sum(1 for result in results if not result.passed),
        "anomaly_count": len(anomalies),
        "critical_anomaly_count": sum(1 for item in anomalies if item["severity"] == "critical"),
        "major_anomaly_count": sum(1 for item in anomalies if item["severity"] == "major"),
        "minor_anomaly_count": sum(1 for item in anomalies if item["severity"] == "minor"),
        "verticals": sorted({result.vertical for result in results}),
        "providers": sorted({round_result.provider for round_result in all_rounds}),
        "pipelines": sorted({round_result.pipeline for round_result in all_rounds}),
        "average_latency_ms": round(sum(round_result.latency_ms for round_result in all_rounds) / max(1, len(all_rounds))),
        "anomalies": anomalies,
        "scenarios": [scenario_summary(result) for result in results],
    }


def scenario_summary(result: ScenarioRunResult) -> dict[str, Any]:
    return {
        "id": result.id,
        "label": result.label,
        "vertical": result.vertical,
        "passed": result.passed,
        "anomaly_count": result.anomaly_count,
        "signal_hits": result.signal_hits,
        "expected_signals": result.expected_signals,
        "rounds": [
            {
                "round_number": round_result.round_number,
                "passed": round_result.passed,
                "latency_ms": round_result.latency_ms,
                "provider": round_result.provider,
                "pipeline": round_result.pipeline,
                "model": round_result.model,
                "names": round_result.names,
                "anomalies": round_result.anomalies,
            }
            for round_result in result.rounds
        ],
    }


def write_artifacts(results: list[ScenarioRunResult], summary: dict[str, Any], output_root: Path) -> Path:
    run_dir = output_root / str(summary["run_id"])
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "results.json").write_text(
        json.dumps([to_plain_data(asdict(result)) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "report.md").write_text(render_markdown_report(summary), encoding="utf-8")
    latest_dir = output_root / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    (latest_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (latest_dir / "report.md").write_text(render_markdown_report(summary), encoding="utf-8")
    return run_dir


def render_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# NamEngine Generation QA",
        "",
        f"- Run: `{summary['run_id']}`",
        f"- Mode: {summary['mode']}",
        f"- Scenarios: {summary['scenario_count']}",
        f"- Passed: {summary['passed_count']}",
        f"- Failed: {summary['failed_count']}",
        f"- Anomalies: {summary['anomaly_count']} ({summary['critical_anomaly_count']} critical, {summary['major_anomaly_count']} major, {summary['minor_anomaly_count']} minor)",
        f"- Verticals: {', '.join(summary['verticals'])}",
        f"- Average latency: {summary['average_latency_ms']} ms",
        "",
        "## Anomalies",
        "",
    ]
    if summary["anomalies"]:
        for anomaly in summary["anomalies"]:
            lines.append(
                f"- **{anomaly['severity']}** `{anomaly['code']}` — {anomaly['scenario_id']} round {anomaly['round']}: {anomaly['message']}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Scenario outputs", ""])
    for scenario in summary["scenarios"]:
        status = "PASS" if scenario["passed"] else "FAIL"
        lines.append(f"### {scenario['label']} — {status}")
        lines.append(f"- Vertical: {scenario['vertical']}")
        lines.append(f"- Signal hits: {', '.join(scenario['signal_hits']) or 'none'}")
        for round_result in scenario["rounds"]:
            lines.append(f"- Round {round_result['round_number']}: {', '.join(round_result['names'])}")
        lines.append("")
    return "\n".join(lines)


def _result_text(result: NameResult) -> str:
    return " ".join(
        str(part)
        for part in [
            result.name,
            result.tagline,
            result.origin,
            result.meaning,
            result.why_this_name,
            result.fit_note,
            result.recommendation_reason,
            " ".join(result.tags),
            json.dumps(result.scores, ensure_ascii=False),
        ]
        if part
    )


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def run_generation_quality(
    *,
    mode: str = "fast",
    use_ai: bool = False,
    scenario_file: Path | str = DEFAULT_SCENARIO_PATH,
    out_dir: Path | str = DEFAULT_OUTPUT_ROOT,
    scenario_ids: list[str] | None = None,
    verticals: list[str] | None = None,
    include_under_development: bool = False,
    rounds_override: int = 0,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Run simulator scenarios and return the Mission Control-ready summary."""
    if mode not in {"fast", "full"}:
        raise ValueError("mode must be fast or full")
    args = argparse.Namespace(
        fast=mode == "fast",
        full=mode == "full",
        scenario_file=str(scenario_file),
        scenario=scenario_ids or [],
        vertical=verticals or [],
        include_under_development=include_under_development,
        rounds=rounds_override,
        use_ai=use_ai,
        out_dir=str(out_dir),
        no_write=not write_outputs,
    )
    scenarios = select_scenarios(load_scenarios(args.scenario_file), args)
    run_id = "generation-qa-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    results = [run_scenario(scenario, use_ai=use_ai, rounds_override=rounds_override) for scenario in scenarios]
    summary = summarize_run(results, run_id=run_id, use_ai=use_ai)
    if write_outputs:
        run_dir = write_artifacts(results, summary, Path(out_dir))
        summary["artifact_dir"] = str(run_dir)
        summary["report_path"] = str(run_dir / "report.md")
        summary["summary_path"] = str(run_dir / "summary.json")
    return summary


def main() -> int:
    args = parse_args()
    summary = run_generation_quality(
        mode="fast" if args.fast else "full",
        use_ai=args.use_ai,
        scenario_file=args.scenario_file,
        out_dir=args.out_dir,
        scenario_ids=args.scenario,
        verticals=args.vertical,
        include_under_development=args.include_under_development,
        rounds_override=args.rounds,
        write_outputs=not args.no_write,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["critical_anomaly_count"] == 0 and summary["major_anomaly_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
