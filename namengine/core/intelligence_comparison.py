"""Stable comparison and regression detection for Baby Intelligence runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

from namengine.core.intelligence_runs import BabyIntelligenceRun


DEFAULT_REGRESSION_THRESHOLD = 0.01
_LOWER_IS_BETTER = {"fallback_rate", "warning_rate", "failure_rate", "latency_ms"}


@dataclass(frozen=True, slots=True)
class IntelligenceDelta:
    metric: str
    baseline: float
    current: float
    delta: float


@dataclass(frozen=True, slots=True)
class IntelligenceRegression:
    code: str
    severity: Literal["critical", "major", "minor", "informational"]
    fixture_id: str
    baseline_value: float | None
    current_value: float | None
    reason: str


@dataclass(frozen=True, slots=True)
class BabyIntelligenceComparison:
    baseline_run_id: str
    current_run_id: str
    compatible: bool
    compatibility_warnings: tuple[str, ...]
    improved_metrics: tuple[IntelligenceDelta, ...]
    regressed_metrics: tuple[IntelligenceDelta, ...]
    unchanged_metrics: tuple[IntelligenceDelta, ...]
    newly_passing_fixtures: tuple[str, ...]
    newly_failing_fixtures: tuple[str, ...]
    largest_gains: tuple[IntelligenceDelta, ...]
    largest_regressions: tuple[IntelligenceDelta, ...]
    regressions: tuple[IntelligenceRegression, ...]
    verdict: Literal["pass", "pass_with_warnings", "regression_detected", "incompatible_comparison"]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compare_baby_intelligence_runs(
    baseline: BabyIntelligenceRun,
    current: BabyIntelligenceRun,
    *,
    threshold: float = DEFAULT_REGRESSION_THRESHOLD,
) -> BabyIntelligenceComparison:
    if not 0 <= threshold <= 0.25:
        raise ValueError("Comparison threshold must be between 0 and 0.25")
    fatal, warnings = _compatibility_findings(baseline, current)
    if fatal:
        return BabyIntelligenceComparison(
            baseline.run_id, current.run_id, False, tuple(fatal + warnings), (), (), (), (), (), (), (), (),
            "incompatible_comparison",
        )

    baseline_metrics = _run_metrics(baseline)
    current_metrics = _run_metrics(current)
    deltas = []
    for metric in sorted(set(baseline_metrics) & set(current_metrics)):
        old = baseline_metrics[metric]
        new = current_metrics[metric]
        deltas.append(IntelligenceDelta(metric, old, new, round(new - old, 6)))
    improved = tuple(item for item in deltas if _directional_delta(item) > threshold)
    regressed = tuple(item for item in deltas if _directional_delta(item) < -threshold)
    unchanged = tuple(item for item in deltas if abs(_directional_delta(item)) <= threshold)

    old_fixtures = _fixture_map(baseline)
    new_fixtures = _fixture_map(current)
    newly_passing = tuple(sorted(key for key in old_fixtures if not old_fixtures[key].passed and new_fixtures[key].passed))
    newly_failing = tuple(sorted(key for key in old_fixtures if old_fixtures[key].passed and not new_fixtures[key].passed))
    regressions = _detect_regressions(baseline, current, threshold, newly_failing, regressed)
    verdict = "regression_detected" if any(item.severity in {"critical", "major"} for item in regressions) else (
        "pass_with_warnings" if regressions or warnings else "pass"
    )
    return BabyIntelligenceComparison(
        baseline_run_id=baseline.run_id,
        current_run_id=current.run_id,
        compatible=True,
        compatibility_warnings=tuple(warnings),
        improved_metrics=tuple(sorted(improved, key=lambda item: item.metric)),
        regressed_metrics=tuple(sorted(regressed, key=lambda item: item.metric)),
        unchanged_metrics=tuple(sorted(unchanged, key=lambda item: item.metric)),
        newly_passing_fixtures=newly_passing,
        newly_failing_fixtures=newly_failing,
        largest_gains=tuple(sorted(improved, key=lambda item: (-_directional_delta(item), item.metric))[:5]),
        largest_regressions=tuple(sorted(regressed, key=lambda item: (_directional_delta(item), item.metric))[:5]),
        regressions=regressions,
        verdict=verdict,
    )


def _compatibility_findings(
    left: BabyIntelligenceRun, right: BabyIntelligenceRun
) -> tuple[list[str], list[str]]:
    structural = ("run_schema_version", "vertical", "fixture_pack_version", "fixture_ids")
    versions = (
        "intake_schema_version", "normalizer_version", "intake_adapter_version",
        "canonical_intent_version", "prompt_version", "quality_adapter_version",
        "evaluation_adapter_version", "model", "provider", "generation_mode",
    )
    fatal = [f"Incompatible {field}" for field in structural if getattr(left, field) != getattr(right, field)]
    if set(_fixture_map(left)) != set(_fixture_map(right)):
        fatal.append("Incompatible fixture execution set")
    warnings = [f"Version/configuration differs: {field}" for field in versions if getattr(left, field) != getattr(right, field)]
    return fatal, warnings


def _run_metrics(run: BabyIntelligenceRun) -> dict[str, float]:
    values = {
        "aggregate_normalized_score": run.normalized_score,
        "pass_rate": run.pass_rate,
        "fallback_rate": round(sum(item.fallback_used for item in run.fixture_results) / max(1, len(run.fixture_results)), 6),
        "warning_rate": round(run.warning_count / max(1, len(run.fixture_results)), 6),
        "failure_rate": round(run.failure_count / max(1, len(run.fixture_results)), 6),
    }
    latencies = [item.latency_ms for item in run.fixture_results if item.latency_ms is not None]
    if latencies:
        values["latency_ms"] = round(sum(latencies) / len(latencies), 6)
    diversity = [item.diversity.score for item in run.fixture_results if item.diversity.score is not None]
    if diversity:
        values["candidate_diversity"] = round(sum(diversity) / len(diversity), 6)
    for metric in run.metric_summaries:
        if metric.value is not None:
            values[f"baby_metric.{metric.code}"] = metric.value
    for fixture in run.fixture_results:
        values[f"fixture.{_fixture_key(fixture)}"] = fixture.normalized_score
        for criterion in fixture.criterion_results:
            maximum = float(criterion.get("maximum_score") or 0.0)
            if maximum:
                values[f"criterion.{_fixture_key(fixture)}.{criterion.get('criterion')}"] = round(
                    float(criterion.get("score") or 0.0) / maximum, 6
                )
    return values


def _fixture_map(run: BabyIntelligenceRun):
    return {_fixture_key(item): item for item in run.fixture_results}


def _fixture_key(fixture) -> str:
    return f"{fixture.fixture_id}#{fixture.repeat_index}"


def _detect_regressions(
    baseline: BabyIntelligenceRun,
    current: BabyIntelligenceRun,
    threshold: float,
    newly_failing: tuple[str, ...],
    regressed: tuple[IntelligenceDelta, ...],
) -> tuple[IntelligenceRegression, ...]:
    findings: list[IntelligenceRegression] = []
    for fixture_id in newly_failing:
        findings.append(IntelligenceRegression(
            "fixture_became_failing", "major", fixture_id, 1.0, 0.0,
            "A previously passing fixture now fails",
        ))
    critical_criteria = {"privacy_safety", "prohibited_names", "prohibited_patterns"}
    old = _fixture_map(baseline)
    new = _fixture_map(current)
    for fixture_id in sorted(old):
        old_criteria = {item.get("criterion"): item for item in old[fixture_id].criterion_results}
        new_criteria = {item.get("criterion"): item for item in new[fixture_id].criterion_results}
        for criterion in critical_criteria:
            before = old_criteria.get(criterion, {}).get("status")
            after = new_criteria.get(criterion, {}).get("status")
            if before != "fail" and after == "fail":
                findings.append(IntelligenceRegression(
                    f"critical_{criterion}", "critical", fixture_id, 1.0, 0.0,
                    f"Critical criterion {criterion} became failing",
                ))
    for delta in regressed:
        if delta.metric.startswith("fixture.") or delta.metric.startswith("criterion."):
            continue
        severity = "major" if _directional_delta(delta) <= -max(0.05, threshold) else "minor"
        findings.append(IntelligenceRegression(
            f"metric_{delta.metric}"[:100], severity, "", delta.baseline, delta.current,
            f"{delta.metric} changed adversely by {abs(delta.delta):.3f}",
        ))
    severity_order = {"critical": 0, "major": 1, "minor": 2, "informational": 3}
    return tuple(sorted(findings, key=lambda item: (severity_order[item.severity], item.code, item.fixture_id)))


def _directional_delta(delta: IntelligenceDelta) -> float:
    return -delta.delta if delta.metric in _LOWER_IS_BETTER else delta.delta
