"""Baby-specific criteria for Name Evaluation Framework v1."""

from __future__ import annotations

from typing import Any

from namengine.core.baby_quality_adapter import evaluate_baby_result_list
from namengine.core.name_evaluation import (
    AdapterAssessment,
    EvaluationPackAdapter,
    NameEvaluationFixture,
    register_evaluation_adapter,
)
from namengine.core.schemas import NameResult, NamingBrief
from namengine.core.validation import is_baby_name_allowed_for_gender


BABY_EVALUATION_ADAPTER_VERSION = "baby-evaluation-pack-v1"


def _attribute(
    attribute: str,
    fixture: NameEvaluationFixture,
    brief: NamingBrief,
    results: list[NameResult],
    parameters: dict[str, Any],
) -> AdapterAssessment:
    value = evaluate_baby_result_list(brief, results).get(attribute)
    if value is None:
        return AdapterAssessment("not_applicable", 0.0, f"{attribute} was not available")
    minimum = float(parameters.get("minimum", 0.6))
    passed = value >= minimum
    return AdapterAssessment(
        "pass" if passed else "fail",
        min(1.0, value / max(minimum, 0.001)),
        f"{attribute.replace('_', ' ').title()} is {value:.3f}; minimum {minimum:.3f}",
        {"value": value, "minimum": minimum},
    )


def _range(
    dimension: str,
    invert: bool,
    fixture: NameEvaluationFixture,
    brief: NamingBrief,
    results: list[NameResult],
    parameters: dict[str, Any],
) -> AdapterAssessment:
    values: list[float] = []
    for result in results:
        raw = result.scores.get(dimension)
        quality = result.metadata.get("quality_scores", {})
        if not isinstance(raw, (int, float)) and isinstance(quality, dict):
            raw = quality.get(dimension)
        if isinstance(raw, (int, float)):
            values.append(1.0 - float(raw) if invert else float(raw))
    if not values:
        return AdapterAssessment("not_applicable", 0.0, f"No {dimension} scores were available")
    average = sum(values) / len(values)
    minimum = float(parameters.get("minimum", 0.0))
    maximum = float(parameters.get("maximum", 1.0))
    passed = minimum <= average <= maximum
    distance = 0.0 if passed else min(abs(average - minimum), abs(average - maximum))
    return AdapterAssessment(
        "pass" if passed else "fail",
        1.0 if passed else max(0.0, 1.0 - distance),
        f"Average {'familiarity' if invert else dimension} is {average:.3f}; expected {minimum:.3f}-{maximum:.3f}",
        {"average": round(average, 3), "minimum": minimum, "maximum": maximum},
    )


def _gender_fit(
    fixture: NameEvaluationFixture,
    brief: NamingBrief,
    results: list[NameResult],
    parameters: dict[str, Any],
) -> AdapterAssessment:
    gender = str(brief.inputs.get("gender") or "").strip().lower()
    if not gender or gender in {"neutral", "gender-neutral", "no preference"}:
        return AdapterAssessment("not_applicable", 0.0, "No binary gender direction applies")
    allowed = sum(is_baby_name_allowed_for_gender(brief, result.name) for result in results)
    ratio = allowed / len(results) if results else 0.0
    minimum = float(parameters.get("minimum_ratio", 1.0))
    return AdapterAssessment(
        "pass" if ratio >= minimum else "fail",
        ratio,
        f"Gender-compatible candidates: {allowed}/{len(results)} for {gender}",
        {"gender": gender, "ratio": round(ratio, 3)},
    )


def _attribute_handler(attribute: str):
    return lambda fixture, brief, results, parameters: _attribute(
        attribute, fixture, brief, results, parameters
    )


BABY_EVALUATION_ADAPTER = EvaluationPackAdapter(
    vertical_slug="baby",
    version=BABY_EVALUATION_ADAPTER_VERSION,
    criterion_handlers={
        "familiarity_range": lambda fixture, brief, results, parameters: _range(
            "distinctiveness", True, fixture, brief, results, parameters
        ),
        "distinctiveness_range": lambda fixture, brief, results, parameters: _range(
            "distinctiveness", False, fixture, brief, results, parameters
        ),
        "cultural_relevance": _attribute_handler("cultural_context_alignment"),
        "gender_fit": _gender_fit,
        "style_fit": _attribute_handler("style_alignment"),
        "sound_strength_fit": _attribute_handler("sound_alignment"),
    },
)

register_evaluation_adapter(BABY_EVALUATION_ADAPTER)
