"""Versioned, cross-vertical name evaluation fixtures and pack scoring."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from namengine.core.briefs import build_brief
from namengine.core.generation import generate_names
from namengine.core.schemas import NameResult, NamingBrief


FIXTURE_SCHEMA_VERSION = "name-evaluation-fixture-v1"
DEFAULT_PACK_ROOT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "name_evaluation"
MAX_FIXTURE_BYTES = 128_000
MAX_OUTPUT_ITEMS = 100
MAX_TEXT_LENGTH = 500

CriterionStatus = Literal["pass", "fail", "not_applicable"]


class FixtureValidationError(ValueError):
    """Raised when evaluation fixture data violates the shared contract."""


@dataclass(frozen=True, slots=True)
class AcceptanceCriterion:
    criterion: str
    weight: float
    required: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NameEvaluationFixture:
    fixture_id: str
    schema_version: str
    vertical: str
    title: str
    description: str
    intake: dict[str, Any]
    expected_naming_territories: tuple[str, ...]
    desired_qualities: tuple[str, ...]
    prohibited_qualities: tuple[str, ...]
    criteria: tuple[AcceptanceCriterion, ...]
    minimum_normalized_score: float = 0.75
    reference_candidates: tuple[str, ...] = ()
    rejection_candidates: tuple[str, ...] = ()
    regression_notes: str = ""
    tags: tuple[str, ...] = ()
    enabled: bool = True
    intake_schema_version: str = ""
    expected_canonical_intent_attributes: dict[str, Any] = field(default_factory=dict)
    expected_normalization_warnings: tuple[str, ...] = ()
    expected_migration_behavior: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AdapterAssessment:
    status: CriterionStatus
    fraction: float
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


AdapterCriterionHandler = Callable[
    [NameEvaluationFixture, NamingBrief, list[NameResult], dict[str, Any]],
    AdapterAssessment,
]


@dataclass(frozen=True, slots=True)
class EvaluationPackAdapter:
    vertical_slug: str
    version: str
    criterion_handlers: dict[str, AdapterCriterionHandler]

    def __post_init__(self) -> None:
        if not self.vertical_slug or self.vertical_slug != self.vertical_slug.strip().lower():
            raise ValueError("Evaluation adapter vertical slugs must be lowercase")
        if not self.version.strip() or not self.criterion_handlers:
            raise ValueError("Evaluation adapters require a version and criterion handlers")
        unknown = set(self.criterion_handlers) & SHARED_CRITERIA
        if unknown:
            raise ValueError(f"Evaluation adapter duplicates shared criteria: {sorted(unknown)}")


@dataclass(frozen=True, slots=True)
class CriterionResult:
    criterion: str
    status: CriterionStatus
    score: float
    maximum_score: float
    required: bool
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FixtureEvaluationResult:
    fixture_id: str
    vertical: str
    passed: bool
    total_score: float
    maximum_score: float
    normalized_score: float
    criterion_results: tuple[CriterionResult, ...]
    failure_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    evaluated_candidates: tuple[str, ...]
    prompt_version: str
    adapter_version: str
    model: str
    providers: tuple[str, ...]
    intake_schema_version: str = ""
    normalizer_version: str = ""
    intake_adapter_version: str = ""
    canonical_intent_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _safe_json_value(asdict(self))


@dataclass(frozen=True, slots=True)
class EvaluationPackSummary:
    fixture_count: int
    passed_count: int
    failed_count: int
    total_score: float
    maximum_score: float
    normalized_score: float
    results: tuple[FixtureEvaluationResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return _safe_json_value(asdict(self))


SHARED_CRITERIA = frozenset(
    {
        "required_candidate_count",
        "uniqueness",
        "duplicate_prevention",
        "prohibited_names",
        "prohibited_patterns",
        "territory_coverage",
        "desired_quality_coverage",
        "prohibited_quality_absence",
        "explanation_completeness",
        "metadata_completeness",
        "valid_bounded_scores",
        "deterministic_ordering",
        "privacy_safety",
    }
)

_ADAPTERS: dict[str, EvaluationPackAdapter] = {}


def register_evaluation_adapter(adapter: EvaluationPackAdapter) -> None:
    existing = _ADAPTERS.get(adapter.vertical_slug)
    if existing is not None and existing != adapter:
        raise ValueError(f"An evaluation adapter is already registered for {adapter.vertical_slug}")
    _ADAPTERS[adapter.vertical_slug] = adapter


def evaluation_adapter_for(vertical_slug: str) -> EvaluationPackAdapter | None:
    return _ADAPTERS.get(vertical_slug.strip().lower())


def load_evaluation_pack(
    path: Path | str,
    *,
    vertical: str | None = None,
    tags: set[str] | None = None,
    include_disabled: bool = False,
) -> list[NameEvaluationFixture]:
    """Load and validate a directory (or file) of versioned fixtures."""
    import namengine.core.evaluation_adapters  # Registers built-in packs.

    root = Path(path)
    if not root.exists():
        raise FixtureValidationError(f"Evaluation pack path does not exist: {root}")
    files = [root] if root.is_file() else sorted(root.glob("*.json"))
    files = [item for item in files if item.name != "schema.json"]
    if not files:
        raise FixtureValidationError(f"Evaluation pack contains no fixtures: {root}")
    fixtures: list[NameEvaluationFixture] = []
    seen: set[str] = set()
    for fixture_path in files:
        if fixture_path.stat().st_size > MAX_FIXTURE_BYTES:
            raise FixtureValidationError(f"Fixture is too large: {fixture_path.name}")
        try:
            payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FixtureValidationError(f"Malformed fixture {fixture_path.name}") from exc
        fixture = validate_fixture(payload, source=fixture_path.name)
        if fixture.fixture_id in seen:
            raise FixtureValidationError(f"Duplicate fixture ID: {fixture.fixture_id}")
        seen.add(fixture.fixture_id)
        fixtures.append(fixture)

    selected = fixtures
    if not include_disabled:
        selected = [fixture for fixture in selected if fixture.enabled]
    if vertical:
        selected = [fixture for fixture in selected if fixture.vertical == vertical]
    if tags:
        selected = [fixture for fixture in selected if tags & set(fixture.tags)]
    return selected


def validate_fixture(payload: Any, *, source: str = "fixture") -> NameEvaluationFixture:
    import namengine.core.evaluation_adapters  # Registers built-in packs.
    from namengine.verticals import VERTICALS

    if not isinstance(payload, dict):
        raise FixtureValidationError(f"{source}: fixture must be an object")
    required = {
        "fixture_id",
        "schema_version",
        "vertical",
        "title",
        "description",
        "intake",
        "expected_naming_territories",
        "desired_qualities",
        "prohibited_qualities",
        "acceptance_criteria",
        "regression_notes",
        "tags",
        "enabled",
    }
    allowed = required | {
        "reference_candidates",
        "rejection_candidates",
        "intake_schema_version",
        "expected_canonical_intent_attributes",
        "expected_normalization_warnings",
        "expected_migration_behavior",
    }
    missing = required - set(payload)
    if missing:
        raise FixtureValidationError(f"{source}: missing fields {sorted(missing)}")
    extra = set(payload) - allowed
    if extra:
        raise FixtureValidationError(f"{source}: unknown fields {sorted(extra)}")
    if payload["schema_version"] != FIXTURE_SCHEMA_VERSION:
        raise FixtureValidationError(f"{source}: unsupported schema version")
    vertical = _required_string(payload["vertical"], source, "vertical").lower()
    if vertical not in VERTICALS:
        raise FixtureValidationError(f"{source}: invalid vertical {vertical}")
    adapter = evaluation_adapter_for(vertical)
    if adapter is None:
        raise FixtureValidationError(f"{source}: no evaluation adapter for {vertical}")
    criteria_payload = payload["acceptance_criteria"]
    if not isinstance(criteria_payload, dict) or not isinstance(criteria_payload.get("criteria"), list):
        raise FixtureValidationError(f"{source}: acceptance_criteria.criteria must be a list")
    acceptance_extra = set(criteria_payload) - {"minimum_normalized_score", "criteria"}
    if acceptance_extra:
        raise FixtureValidationError(f"{source}: unknown acceptance fields {sorted(acceptance_extra)}")
    minimum = _finite_number(criteria_payload.get("minimum_normalized_score", 0.75), source)
    if not 0 <= minimum <= 1:
        raise FixtureValidationError(f"{source}: minimum_normalized_score must be bounded")
    supported = SHARED_CRITERIA | set(adapter.criterion_handlers)
    criteria: list[AcceptanceCriterion] = []
    for index, row in enumerate(criteria_payload["criteria"]):
        if not isinstance(row, dict):
            raise FixtureValidationError(f"{source}: criterion {index} must be an object")
        criterion_extra = set(row) - {"criterion", "weight", "required", "parameters"}
        if criterion_extra:
            raise FixtureValidationError(f"{source}: unknown criterion fields {sorted(criterion_extra)}")
        name = _required_string(row.get("criterion"), source, "criterion")
        if name not in supported:
            raise FixtureValidationError(f"{source}: unknown criterion {name}")
        weight = _finite_number(row.get("weight"), source)
        if weight <= 0:
            raise FixtureValidationError(f"{source}: criterion weights must be positive")
        parameters = row.get("parameters", {})
        if not isinstance(parameters, dict):
            raise FixtureValidationError(f"{source}: criterion parameters must be an object")
        if "required" in row and not isinstance(row["required"], bool):
            raise FixtureValidationError(f"{source}: criterion required must be boolean")
        _validate_json_data(parameters, source)
        _validate_criterion_parameters(name, parameters, source)
        criteria.append(
            AcceptanceCriterion(
                criterion=name,
                weight=weight,
                required=bool(row.get("required", True)),
                parameters=parameters,
            )
        )
    if not criteria:
        raise FixtureValidationError(f"{source}: at least one criterion is required")
    if len({criterion.criterion for criterion in criteria}) != len(criteria):
        raise FixtureValidationError(f"{source}: duplicate criteria are not allowed")
    intake = payload["intake"]
    if not isinstance(intake, dict):
        raise FixtureValidationError(f"{source}: intake must be an object")
    if not isinstance(payload["enabled"], bool):
        raise FixtureValidationError(f"{source}: enabled must be boolean")
    _validate_json_data(intake, source)
    intake_schema_version = str(payload.get("intake_schema_version") or "").strip()
    expected_intent = payload.get("expected_canonical_intent_attributes", {})
    expected_migration = payload.get("expected_migration_behavior", {})
    if not isinstance(expected_intent, dict) or not isinstance(expected_migration, dict):
        raise FixtureValidationError(f"{source}: intake expectations must be objects")
    _validate_json_data(expected_intent, source)
    _validate_json_data(expected_migration, source)
    return NameEvaluationFixture(
        fixture_id=_required_string(payload["fixture_id"], source, "fixture_id"),
        schema_version=FIXTURE_SCHEMA_VERSION,
        vertical=vertical,
        title=_bounded_string(payload["title"], source, "title"),
        description=_bounded_string(payload["description"], source, "description"),
        intake=dict(intake),
        expected_naming_territories=_string_tuple(payload["expected_naming_territories"], source),
        desired_qualities=_string_tuple(payload["desired_qualities"], source),
        prohibited_qualities=_string_tuple(payload["prohibited_qualities"], source),
        criteria=tuple(criteria),
        minimum_normalized_score=minimum,
        reference_candidates=_string_tuple(payload.get("reference_candidates", []), source),
        rejection_candidates=_string_tuple(payload.get("rejection_candidates", []), source),
        regression_notes=_bounded_string(payload["regression_notes"], source, "regression_notes"),
        tags=_string_tuple(payload["tags"], source),
        enabled=payload["enabled"],
        intake_schema_version=intake_schema_version,
        expected_canonical_intent_attributes=dict(expected_intent),
        expected_normalization_warnings=_string_tuple(
            payload.get("expected_normalization_warnings", []), source
        ),
        expected_migration_behavior=dict(expected_migration),
    )


def evaluate_fixture(
    fixture: NameEvaluationFixture,
    results: list[NameResult],
    *,
    comparison_results: list[NameResult] | None = None,
) -> FixtureEvaluationResult:
    import namengine.core.evaluation_adapters  # Registers built-in packs.
    from namengine.verticals import get_vertical

    adapter = evaluation_adapter_for(fixture.vertical)
    if adapter is None:
        raise FixtureValidationError(f"No evaluation adapter for {fixture.vertical}")
    brief = build_brief(get_vertical(fixture.vertical), fixture.intake)
    criterion_results = tuple(
        _evaluate_criterion(fixture, brief, results, comparison_results, adapter, criterion)
        for criterion in fixture.criteria
    )
    intake_results, intake_metadata = _evaluate_intake_expectations(fixture)
    criterion_results += intake_results
    total = round(sum(item.score for item in criterion_results), 3)
    maximum = round(sum(item.maximum_score for item in criterion_results), 3)
    normalized = round(total / maximum, 3) if maximum else 0.0
    failures = tuple(
        item.reason for item in criterion_results if item.status == "fail" and item.required
    )
    warnings = tuple(
        item.reason
        for item in criterion_results
        if item.status == "fail" and not item.required
    )
    metadata = results[0].metadata if results else {}
    providers = sorted(
        {
            str(result.metadata.get("provider") or result.metadata.get("source") or "unknown")
            for result in results
        }
    )
    passed = not failures and normalized >= fixture.minimum_normalized_score
    if normalized < fixture.minimum_normalized_score:
        failures = failures + (
            f"Normalized score {normalized:.3f} is below {fixture.minimum_normalized_score:.3f}",
        )
    return FixtureEvaluationResult(
        fixture_id=fixture.fixture_id,
        vertical=fixture.vertical,
        passed=passed,
        total_score=total,
        maximum_score=maximum,
        normalized_score=normalized,
        criterion_results=criterion_results,
        failure_reasons=failures,
        warnings=warnings,
        evaluated_candidates=tuple((result.id or result.name)[:MAX_TEXT_LENGTH] for result in results[:MAX_OUTPUT_ITEMS]),
        prompt_version=str(metadata.get("prompt_version") or "unknown")[:MAX_TEXT_LENGTH],
        adapter_version=adapter.version[:MAX_TEXT_LENGTH],
        model=str(metadata.get("model") or "unknown")[:MAX_TEXT_LENGTH],
        providers=tuple(item[:MAX_TEXT_LENGTH] for item in providers[:MAX_OUTPUT_ITEMS]),
        intake_schema_version=intake_metadata.get("intake_schema_version", ""),
        normalizer_version=intake_metadata.get("normalizer_version", ""),
        intake_adapter_version=intake_metadata.get("intake_adapter_version", ""),
        canonical_intent_version=intake_metadata.get("canonical_intent_version", ""),
    )


def evaluate_generated_fixture(
    fixture: NameEvaluationFixture, *, use_ai: bool = False
) -> FixtureEvaluationResult:
    from namengine.verticals import get_vertical

    vertical = get_vertical(fixture.vertical)
    brief = build_brief(vertical, fixture.intake)
    results = generate_names(vertical, brief, use_ai=use_ai)
    comparison = None
    if any(item.criterion == "deterministic_ordering" for item in fixture.criteria):
        comparison = generate_names(vertical, brief, use_ai=use_ai)
    return evaluate_fixture(fixture, results, comparison_results=comparison)


def _evaluate_intake_expectations(
    fixture: NameEvaluationFixture,
) -> tuple[tuple[CriterionResult, ...], dict[str, str]]:
    """Evaluate optional, cross-vertical normalization expectations."""
    from namengine.core.intake import normalize_intake

    normalized = normalize_intake(
        fixture.vertical,
        fixture.intake,
        intake_version=fixture.intake_schema_version or None,
        allow_partial=True,
    )
    metadata = normalized.version_metadata() if normalized.valid else {}
    has_expectations = bool(
        fixture.intake_schema_version
        or fixture.expected_canonical_intent_attributes
        or fixture.expected_normalization_warnings
        or fixture.expected_migration_behavior
    )
    if not has_expectations:
        return (), metadata
    if not normalized.valid or normalized.canonical_intent is None:
        return (
            CriterionResult(
                "intake_normalization",
                "fail",
                0.0,
                1.0,
                True,
                "Fixture intake could not be normalized",
                {"error_codes": [item.code for item in normalized.validation.errors]},
            ),
        ), metadata

    results: list[CriterionResult] = []
    if fixture.expected_canonical_intent_attributes:
        actual = normalized.canonical_intent.to_dict()
        mismatches = sorted(
            path
            for path, expected in fixture.expected_canonical_intent_attributes.items()
            if _nested_value(actual, path) != expected
        )
        results.append(
            CriterionResult(
                "canonical_intent_expectations",
                "fail" if mismatches else "pass",
                0.0 if mismatches else 1.0,
                1.0,
                True,
                "Canonical intent expectations differ" if mismatches else "Canonical intent expectations match",
                {"mismatched_paths": mismatches[:MAX_OUTPUT_ITEMS]},
            )
        )
    if fixture.expected_normalization_warnings:
        actual_warnings = {
            item.code for item in normalized.validation_warnings
        } | set(normalized.deprecation_warnings) | set(normalized.migration_warnings)
        missing = sorted(set(fixture.expected_normalization_warnings) - actual_warnings)
        results.append(
            CriterionResult(
                "normalization_warning_expectations",
                "fail" if missing else "pass",
                0.0 if missing else 1.0,
                1.0,
                True,
                "Expected normalization warnings are missing" if missing else "Expected normalization warnings are present",
                {"missing_warnings": missing[:MAX_OUTPUT_ITEMS]},
            )
        )
    if fixture.expected_migration_behavior:
        actual_migration = {
            "source_version": normalized.migration_source_version,
            "destination_version": normalized.migration_destination_version,
            "history": list(normalized.migration_history),
        }
        mismatches = sorted(
            key
            for key, expected in fixture.expected_migration_behavior.items()
            if actual_migration.get(key) != expected
        )
        results.append(
            CriterionResult(
                "migration_expectations",
                "fail" if mismatches else "pass",
                0.0 if mismatches else 1.0,
                1.0,
                True,
                "Migration expectations differ" if mismatches else "Migration expectations match",
                {"mismatched_fields": mismatches[:MAX_OUTPUT_ITEMS]},
            )
        )
    return tuple(results), metadata


def _nested_value(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def summarize_evaluation_pack(
    results: list[FixtureEvaluationResult],
) -> EvaluationPackSummary:
    ordered = tuple(sorted(results, key=lambda item: (item.vertical, item.fixture_id)))
    total = round(sum(item.total_score for item in ordered), 3)
    maximum = round(sum(item.maximum_score for item in ordered), 3)
    return EvaluationPackSummary(
        fixture_count=len(ordered),
        passed_count=sum(1 for item in ordered if item.passed),
        failed_count=sum(1 for item in ordered if not item.passed),
        total_score=total,
        maximum_score=maximum,
        normalized_score=round(total / maximum, 3) if maximum else 0.0,
        results=ordered,
    )


def serialize_evaluation(value: FixtureEvaluationResult | EvaluationPackSummary) -> str:
    return json.dumps(value.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _evaluate_criterion(
    fixture: NameEvaluationFixture,
    brief: NamingBrief,
    results: list[NameResult],
    comparison: list[NameResult] | None,
    adapter: EvaluationPackAdapter,
    criterion: AcceptanceCriterion,
) -> CriterionResult:
    if criterion.criterion in SHARED_CRITERIA:
        assessment = _evaluate_shared(criterion.criterion, fixture, results, comparison, criterion.parameters)
    else:
        assessment = adapter.criterion_handlers[criterion.criterion](
            fixture, brief, results, criterion.parameters
        )
    fraction = _bounded_fraction(assessment.fraction)
    maximum = 0.0 if assessment.status == "not_applicable" else criterion.weight
    score = 0.0 if assessment.status == "not_applicable" else criterion.weight * fraction
    return CriterionResult(
        criterion=criterion.criterion,
        status=assessment.status,
        score=round(score, 3),
        maximum_score=round(maximum, 3),
        required=criterion.required,
        reason=assessment.reason[:MAX_TEXT_LENGTH],
        details=_safe_json_value(assessment.details),
    )


def _evaluate_shared(
    name: str,
    fixture: NameEvaluationFixture,
    results: list[NameResult],
    comparison: list[NameResult] | None,
    parameters: dict[str, Any],
) -> AdapterAssessment:
    names = [result.name.strip() for result in results if result.name.strip()]
    normalized_names = [_normalize(item) for item in names]
    haystacks = [_candidate_text(result) for result in results]
    if name == "required_candidate_count":
        minimum = int(parameters.get("minimum", parameters.get("exact", 1)))
        maximum = int(parameters.get("maximum", parameters.get("exact", 10_000)))
        passed = minimum <= len(results) <= maximum
        fraction = min(1.0, len(results) / max(1, minimum)) if len(results) <= maximum else 0.0
        return _assessment(passed, fraction, f"Returned {len(results)} candidates; expected {minimum}-{maximum}")
    if name in {"uniqueness", "duplicate_prevention"}:
        unique = len(set(normalized_names))
        ratio = unique / len(normalized_names) if normalized_names else 0.0
        threshold = float(parameters.get("minimum_ratio", 1.0))
        return _assessment(ratio >= threshold, ratio, f"Unique candidate ratio is {ratio:.3f}")
    if name == "prohibited_names":
        prohibited = {_normalize(item) for item in fixture.rejection_candidates}
        prohibited.update(_normalize(item) for item in parameters.get("names", []))
        hits = sorted(name for name in names if _normalize(name) in prohibited)
        return _assessment(not hits, 1.0 if not hits else 0.0, f"Prohibited name hits: {hits or 'none'}", {"hits": hits})
    if name == "prohibited_patterns":
        patterns = [str(item) for item in parameters.get("patterns", [])]
        hits = sorted({pattern for pattern in patterns for text in haystacks if re.search(pattern, text, re.IGNORECASE)})
        return _assessment(not hits, 1.0 if not hits else 0.0, f"Prohibited pattern hits: {hits or 'none'}", {"hits": hits})
    if name in {"territory_coverage", "desired_quality_coverage"}:
        terms = fixture.expected_naming_territories if name == "territory_coverage" else fixture.desired_qualities
        hits = [term for term in terms if any(_term_matches(term, text) for text in haystacks)]
        ratio = len(hits) / len(terms) if terms else 1.0
        minimum = float(parameters.get("minimum_ratio", 0.5))
        return _assessment(ratio >= minimum, ratio, f"Covered {len(hits)} of {len(terms)} requested signals", {"hits": hits})
    if name == "prohibited_quality_absence":
        hits = [term for term in fixture.prohibited_qualities if any(_term_matches(term, text) for text in haystacks)]
        ratio = 1.0 - len(hits) / len(fixture.prohibited_qualities) if fixture.prohibited_qualities else 1.0
        return _assessment(not hits, ratio, f"Prohibited quality hits: {hits or 'none'}", {"hits": hits})
    if name == "explanation_completeness":
        complete = sum(bool(result.why_this_name.strip() and result.fit_note.strip()) for result in results)
        ratio = complete / len(results) if results else 0.0
        minimum = float(parameters.get("minimum_ratio", 1.0))
        return _assessment(ratio >= minimum, ratio, f"Complete explanations: {complete}/{len(results)}")
    if name == "metadata_completeness":
        fields = [str(item) for item in parameters.get("required_fields", ["prompt_version", "quality_score_version", "quality_scores"])]
        complete = sum(all(_metadata_path(result.metadata, field) is not None for field in fields) for result in results)
        ratio = complete / len(results) if results else 0.0
        minimum = float(parameters.get("minimum_ratio", 1.0))
        return _assessment(ratio >= minimum, ratio, f"Complete metadata: {complete}/{len(results)}", {"required_fields": fields})
    if name == "valid_bounded_scores":
        checked = 0
        invalid = 0
        for result in results:
            score_maps = [result.scores]
            quality_scores = result.metadata.get("quality_scores")
            if isinstance(quality_scores, dict):
                score_maps.append(quality_scores)
            for scores in score_maps:
                for value in scores.values():
                    checked += 1
                    if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                        invalid += 1
        passed = checked > 0 and invalid == 0
        return _assessment(passed, 1.0 if passed else 0.0, f"Checked {checked} scores; invalid: {invalid}")
    if name == "deterministic_ordering":
        if comparison is None:
            return AdapterAssessment("not_applicable", 0.0, "No identical-input comparison was supplied")
        left = [_normalize(result.name) for result in results]
        right = [_normalize(result.name) for result in comparison]
        return _assessment(left == right, 1.0 if left == right else 0.0, "Identical inputs produced matching order" if left == right else "Identical inputs produced different order")
    if name == "privacy_safety":
        leaks = _metadata_leaks(results)
        return _assessment(not leaks, 1.0 if not leaks else 0.0, f"Unsafe metadata findings: {len(leaks)}", {"findings": leaks})
    raise FixtureValidationError(f"Unknown shared criterion {name}")


def _validate_criterion_parameters(name: str, parameters: dict[str, Any], source: str) -> None:
    if name == "prohibited_patterns":
        for pattern in parameters.get("patterns", []):
            try:
                re.compile(str(pattern))
            except re.error as exc:
                raise FixtureValidationError(f"{source}: invalid prohibited pattern") from exc
    for key, value in parameters.items():
        if key.startswith("minimum_") or key.startswith("maximum_"):
            number = _finite_number(value, source)
            if key.endswith("ratio") and not 0 <= number <= 1:
                raise FixtureValidationError(f"{source}: ratios must be bounded")


def _metadata_leaks(results: list[NameResult]) -> list[str]:
    sensitive_keys = {"api_key", "authorization", "secret", "token", "password", "customer_intake", "stack_trace", "traceback"}
    findings: list[str] = []

    def visit(value: Any, path: str) -> None:
        if len(findings) >= MAX_OUTPUT_ITEMS:
            return
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = str(key).lower().replace("-", "_")
                child = f"{path}.{key}"
                if normalized in sensitive_keys or any(term in normalized for term in ("api_key", "password", "secret")):
                    findings.append(child)
                else:
                    visit(item, child)
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value[:MAX_OUTPUT_ITEMS]):
                visit(item, f"{path}[{index}]")
        elif isinstance(value, str) and ("traceback (most recent call last)" in value.lower() or re.search(r"sk-[A-Za-z0-9]{12,}", value)):
            findings.append(path)

    for index, result in enumerate(results[:MAX_OUTPUT_ITEMS]):
        visit(result.metadata, f"candidate[{index}].metadata")
    return findings


def _candidate_text(result: NameResult) -> str:
    return " ".join(
        [result.name, result.tagline, result.origin, result.meaning, result.why_this_name, result.fit_note, " ".join(result.tags)]
    ).lower()


def _term_matches(term: str, text: str) -> bool:
    tokens = [_normalize(item) for item in re.findall(r"[a-z0-9]+", term.lower()) if len(item) > 2]
    return bool(tokens) and all(token in _normalize(text) for token in tokens)


def _metadata_path(metadata: dict[str, Any], path: str) -> Any:
    value: Any = metadata
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _assessment(passed: bool, fraction: float, reason: str, details: dict[str, Any] | None = None) -> AdapterAssessment:
    return AdapterAssessment("pass" if passed else "fail", fraction, reason, details or {})


def _finite_number(value: Any, source: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise FixtureValidationError(f"{source}: expected a finite number") from exc
    if not math.isfinite(number):
        raise FixtureValidationError(f"{source}: expected a finite number")
    return number


def _bounded_fraction(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("Criterion fractions must be finite")
    return max(0.0, min(1.0, value))


def _required_string(value: Any, source: str, field_name: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > MAX_TEXT_LENGTH:
        raise FixtureValidationError(f"{source}: invalid {field_name}")
    return text


def _bounded_string(value: Any, source: str, field_name: str) -> str:
    text = str(value or "").strip()
    if len(text) > MAX_TEXT_LENGTH:
        raise FixtureValidationError(f"{source}: {field_name} is too long")
    return text


def _string_tuple(value: Any, source: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > MAX_OUTPUT_ITEMS:
        raise FixtureValidationError(f"{source}: expected a bounded string list")
    if any(not isinstance(item, str) for item in value):
        raise FixtureValidationError(f"{source}: list items must be strings")
    return tuple(_bounded_string(item, source, "list item") for item in value)


def _validate_json_data(value: Any, source: str, depth: int = 0) -> None:
    if depth > 10:
        raise FixtureValidationError(f"{source}: intake nesting is too deep")
    if isinstance(value, dict):
        if len(value) > MAX_OUTPUT_ITEMS:
            raise FixtureValidationError(f"{source}: intake has too many fields")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_TEXT_LENGTH:
                raise FixtureValidationError(f"{source}: invalid intake key")
            _validate_json_data(item, source, depth + 1)
        return
    if isinstance(value, list):
        if len(value) > MAX_OUTPUT_ITEMS:
            raise FixtureValidationError(f"{source}: intake list is too long")
        for item in value:
            _validate_json_data(item, source, depth + 1)
        return
    if isinstance(value, str) and len(value) > MAX_TEXT_LENGTH:
        raise FixtureValidationError(f"{source}: intake value is too long")
    if isinstance(value, float) and not math.isfinite(value):
        raise FixtureValidationError(f"{source}: intake numbers must be finite")
    if value is not None and not isinstance(value, (str, bool, int, float)):
        raise FixtureValidationError(f"{source}: intake must contain JSON values")


def _normalize(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _safe_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key)[:MAX_TEXT_LENGTH]: _safe_json_value(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_safe_json_value(item) for item in value[:MAX_OUTPUT_ITEMS]]
    if isinstance(value, str):
        return value[:MAX_TEXT_LENGTH]
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return round(value, 6) if math.isfinite(value) else None
    return str(value)[:MAX_TEXT_LENGTH]
