"""Deterministic, privacy-safe records for naming intelligence runs."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


INTELLIGENCE_RUN_SCHEMA_VERSION = "baby-intelligence-run-v1"
MAX_DIAGNOSTIC_TEXT = 500
MAX_DIAGNOSTIC_ITEMS = 100

MetricStatus = Literal["applicable", "not_applicable"]
RunStatus = Literal[
    "pass",
    "pass_with_warnings",
    "regression_detected",
    "incompatible_comparison",
    "execution_failure",
]


@dataclass(frozen=True, slots=True)
class IntelligenceMetric:
    code: str
    status: MetricStatus
    value: float | None
    reason: str

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("Intelligence metrics require a code")
        if self.status not in {"applicable", "not_applicable"}:
            raise ValueError("Invalid intelligence metric status")
        if self.status == "applicable":
            _bounded_score(self.value, "metric value")
        elif self.value is not None:
            raise ValueError("Not-applicable metrics cannot contain a value")


@dataclass(frozen=True, slots=True)
class CandidateDiagnostic:
    candidate_id: str
    name: str
    final_rank: int
    shared_quality_score: float | None
    baby_quality_dimensions: dict[str, float]
    ranking_contribution: float | None
    territory: str
    explanation_completeness: float
    metadata_completeness: float
    demotion_reasons: tuple[str, ...]
    tie_break_fields: tuple[str, ...]
    reference_candidate: bool
    rejection_candidate: bool
    fallback_origin: str

    def __post_init__(self) -> None:
        if self.final_rank < 1:
            raise ValueError("Candidate rank must be positive")
        if self.shared_quality_score is not None:
            _bounded_score(self.shared_quality_score, "shared quality score")
        if self.ranking_contribution is not None:
            _bounded_score(self.ranking_contribution, "ranking contribution")
        _bounded_score(self.explanation_completeness, "explanation completeness")
        _bounded_score(self.metadata_completeness, "metadata completeness")
        for value in self.baby_quality_dimensions.values():
            _bounded_score(value, "Baby quality dimension")


@dataclass(frozen=True, slots=True)
class DiversityAnalysis:
    status: MetricStatus
    score: float | None
    exact_duplicates: tuple[str, ...] = ()
    normalized_duplicates: tuple[str, ...] = ()
    near_duplicate_pairs: tuple[str, ...] = ()
    repeated_roots: tuple[str, ...] = ()
    repeated_endings: tuple[str, ...] = ()
    repeated_initial_sounds: tuple[str, ...] = ()
    first_letter_concentration: float | None = None
    cultural_concentration: float | None = None
    familiarity_concentration: float | None = None
    style_concentration: float | None = None
    territory_concentration: float | None = None
    ordering_diversity: float | None = None
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status == "applicable":
            _bounded_score(self.score, "diversity score")
        elif self.status != "not_applicable" or self.score is not None:
            raise ValueError("Invalid diversity status")
        for value in (
            self.first_letter_concentration,
            self.cultural_concentration,
            self.familiarity_concentration,
            self.style_concentration,
            self.territory_concentration,
            self.ordering_diversity,
        ):
            if value is not None:
                _bounded_score(value, "diversity concentration")


@dataclass(frozen=True, slots=True)
class FixtureIntelligenceResult:
    fixture_id: str
    repeat_index: int
    passed: bool
    total_score: float
    maximum_score: float
    normalized_score: float
    criterion_results: tuple[dict[str, Any], ...]
    failure_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    candidates: tuple[CandidateDiagnostic, ...]
    metrics: tuple[IntelligenceMetric, ...]
    diversity: DiversityAnalysis
    provider: str
    model: str
    fallback_used: bool
    latency_ms: int | None
    timeout: bool = False
    execution_error: str = ""

    def __post_init__(self) -> None:
        if self.repeat_index < 1:
            raise ValueError("Repeat index must be positive")
        _bounded_nonnegative(self.total_score, "fixture total score")
        _bounded_nonnegative(self.maximum_score, "fixture maximum score")
        _bounded_score(self.normalized_score, "fixture normalized score")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("Latency must be non-negative")


@dataclass(frozen=True, slots=True)
class Weakness:
    code: str
    affected_fixture_ids: tuple[str, ...]
    affected_candidates: tuple[str, ...]
    severity: Literal["critical", "major", "minor", "informational"]
    frequency: int
    weighted_impact: float
    likely_subsystem: str
    explanation: str
    suggested_engineering_target: str

    def __post_init__(self) -> None:
        if self.frequency < 1:
            raise ValueError("Weakness frequency must be positive")
        _bounded_score(self.weighted_impact, "weakness impact")


@dataclass(frozen=True, slots=True)
class BabyIntelligenceRun:
    run_id: str
    run_schema_version: str
    started_at: str
    completed_at: str
    vertical: str
    fixture_pack_version: str
    fixture_ids: tuple[str, ...]
    intake_schema_version: str
    normalizer_version: str
    intake_adapter_version: str
    canonical_intent_version: str
    prompt_version: str
    quality_adapter_version: str
    evaluation_adapter_version: str
    model: str
    provider: str
    generation_mode: str
    fallback_status: str
    fixture_results: tuple[FixtureIntelligenceResult, ...]
    aggregate_score: float
    maximum_score: float
    normalized_score: float
    pass_rate: float
    failure_count: int
    warning_count: int
    metric_summaries: tuple[IntelligenceMetric, ...]
    weaknesses: tuple[Weakness, ...]
    regression_status: RunStatus
    comparison_baseline_id: str = ""
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.run_schema_version != INTELLIGENCE_RUN_SCHEMA_VERSION:
            raise ValueError("Unsupported intelligence run schema")
        if self.vertical != "baby" or not self.run_id.strip():
            raise ValueError("Baby Intelligence run identity is invalid")
        _bounded_nonnegative(self.aggregate_score, "aggregate score")
        _bounded_nonnegative(self.maximum_score, "maximum score")
        _bounded_score(self.normalized_score, "normalized score")
        _bounded_score(self.pass_rate, "pass rate")
        if self.failure_count < 0 or self.warning_count < 0:
            raise ValueError("Run counts must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return _safe_value(asdict(self))

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def audit_metadata(self) -> dict[str, Any]:
        """Allowlisted summary for optional internal audit correlation."""
        return {
            "baby_intelligence_run_id": self.run_id[:MAX_DIAGNOSTIC_TEXT],
            "baby_intelligence_schema_version": self.run_schema_version,
            "baby_intelligence_fixture_pack_version": self.fixture_pack_version,
            "baby_intelligence_normalized_score": self.normalized_score,
            "baby_intelligence_status": self.regression_status,
            "baby_intelligence_fixture_count": len(self.fixture_results),
            "prompt_version": self.prompt_version[:MAX_DIAGNOSTIC_TEXT],
            "intake_schema_version": self.intake_schema_version[:MAX_DIAGNOSTIC_TEXT],
            "quality_adapter_version": self.quality_adapter_version[:MAX_DIAGNOSTIC_TEXT],
            "evaluation_adapter_version": self.evaluation_adapter_version[:MAX_DIAGNOSTIC_TEXT],
        }


def intelligence_run_from_dict(payload: Any) -> BabyIntelligenceRun:
    """Strictly restore a run from a baseline-safe JSON object."""
    if not isinstance(payload, dict):
        raise ValueError("Intelligence run must be an object")
    fixture_results = tuple(_fixture_from_dict(item) for item in payload.get("fixture_results", []))
    data = dict(payload)
    data["fixture_ids"] = tuple(data.get("fixture_ids", []))
    data["fixture_results"] = fixture_results
    data["metric_summaries"] = tuple(IntelligenceMetric(**item) for item in data.get("metric_summaries", []))
    data["weaknesses"] = tuple(_weakness_from_dict(item) for item in data.get("weaknesses", []))
    data["diagnostics"] = tuple(data.get("diagnostics", []))
    try:
        return BabyIntelligenceRun(**data)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid intelligence run record") from exc


def _fixture_from_dict(data: Any) -> FixtureIntelligenceResult:
    if not isinstance(data, dict):
        raise ValueError("Fixture intelligence result must be an object")
    row = dict(data)
    row["criterion_results"] = tuple(row.get("criterion_results", []))
    row["failure_reasons"] = tuple(row.get("failure_reasons", []))
    row["warnings"] = tuple(row.get("warnings", []))
    row["candidates"] = tuple(CandidateDiagnostic(**_tuple_candidate(item)) for item in row.get("candidates", []))
    row["metrics"] = tuple(IntelligenceMetric(**item) for item in row.get("metrics", []))
    diversity = dict(row.get("diversity", {}))
    for key in (
        "exact_duplicates", "normalized_duplicates", "near_duplicate_pairs", "repeated_roots",
        "repeated_endings", "repeated_initial_sounds", "reasons",
    ):
        diversity[key] = tuple(diversity.get(key, []))
    row["diversity"] = DiversityAnalysis(**diversity)
    return FixtureIntelligenceResult(**row)


def _tuple_candidate(data: dict[str, Any]) -> dict[str, Any]:
    row = dict(data)
    row["demotion_reasons"] = tuple(row.get("demotion_reasons", []))
    row["tie_break_fields"] = tuple(row.get("tie_break_fields", []))
    return row


def _weakness_from_dict(data: dict[str, Any]) -> Weakness:
    row = dict(data)
    row["affected_fixture_ids"] = tuple(row.get("affected_fixture_ids", []))
    row["affected_candidates"] = tuple(row.get("affected_candidates", []))
    return Weakness(**row)


def _bounded_score(value: Any, label: str) -> float:
    number = _finite(value, label)
    if not 0 <= number <= 1:
        raise ValueError(f"{label} must be between 0 and 1")
    return number


def _bounded_nonnegative(value: Any, label: str) -> float:
    number = _finite(value, label)
    if number < 0:
        raise ValueError(f"{label} must be non-negative")
    return number


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _safe_value(value: Any, depth: int = 0) -> Any:
    if depth > 12:
        return "[bounded]"
    if isinstance(value, dict):
        return {
            str(key)[:100]: _safe_value(item, depth + 1)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))[:MAX_DIAGNOSTIC_ITEMS]
        }
    if isinstance(value, (list, tuple)):
        return [_safe_value(item, depth + 1) for item in value[:MAX_DIAGNOSTIC_ITEMS]]
    if isinstance(value, str):
        return value[:MAX_DIAGNOSTIC_TEXT]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Intelligence output contains a non-finite number")
        return round(value, 6)
    if value is None or isinstance(value, (bool, int)):
        return value
    raise ValueError("Intelligence output must be JSON-safe")
