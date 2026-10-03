"""Cross-vertical quality adapters and deterministic ranking infrastructure."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
from typing import Any

from namengine.core.generation_prompt_config import (
    generation_model_score_keys,
    generation_prompt_config_or_none,
    generation_prompt_guidance,
)
from namengine.core.schemas import GenerationCandidate, NameResult, NamingBrief


TasteThesisBuilder = Callable[[NamingBrief, dict[str, Any]], str]
DimensionScorer = Callable[[NameResult, NamingBrief], tuple[dict[str, float], list[str]]]
ExplanationImprover = Callable[[list[NameResult], NamingBrief], None]
AttributeEvaluator = Callable[[NamingBrief, list[NameResult]], dict[str, float]]


@dataclass(frozen=True, slots=True)
class QualityAdapter:
    vertical_slug: str
    score_version: str
    score_weights: dict[str, float]
    build_taste_thesis: TasteThesisBuilder
    score_dimensions: DimensionScorer
    improve_explanations: ExplanationImprover | None = None
    evaluate_attributes: AttributeEvaluator | None = None

    def __post_init__(self) -> None:
        if not self.vertical_slug or self.vertical_slug != self.vertical_slug.strip().lower():
            raise ValueError("Quality adapter vertical slugs must be non-empty lowercase values")
        if not self.score_version.strip():
            raise ValueError("Quality adapters require score versions")
        if (
            not self.score_weights
            or any(not math.isfinite(weight) or weight < 0 for weight in self.score_weights.values())
            or abs(sum(self.score_weights.values()) - 1.0) > 0.001
        ):
            raise ValueError("Quality adapter score weights must total 1.0")


_ADAPTERS: dict[str, QualityAdapter] = {}


def register_quality_adapter(adapter: QualityAdapter) -> None:
    existing = _ADAPTERS.get(adapter.vertical_slug)
    if existing is not None and existing != adapter:
        raise ValueError(f"A quality adapter is already registered for {adapter.vertical_slug}")
    _ADAPTERS[adapter.vertical_slug] = adapter


def unregister_quality_adapter(vertical_slug: str) -> None:
    """Remove a dynamically registered adapter (primarily useful for isolated tests)."""
    slug = vertical_slug.strip().lower()
    _ADAPTERS.pop(slug, None)


def quality_adapter_for(vertical_slug: str) -> QualityAdapter | None:
    return _ADAPTERS.get(vertical_slug.strip().lower())


def build_quality_taste_thesis(
    vertical_slug: str, brief: NamingBrief, weighting: dict[str, Any]
) -> str | None:
    adapter = quality_adapter_for(vertical_slug)
    return adapter.build_taste_thesis(brief, weighting) if adapter else None


def improve_quality_explanations(
    vertical_slug: str, results: list[NameResult], brief: NamingBrief
) -> None:
    adapter = quality_adapter_for(vertical_slug)
    if adapter and adapter.improve_explanations:
        adapter.improve_explanations(results, brief)


def score_quality_result(
    vertical_slug: str, result: NameResult, brief: NamingBrief
) -> tuple[float, list[str]] | None:
    adapter = quality_adapter_for(vertical_slug)
    if not adapter:
        return None
    dimensions, reasons = adapter.score_dimensions(result, brief)
    missing = set(adapter.score_weights) - set(dimensions)
    if missing:
        raise ValueError(f"Quality scorer omitted dimensions: {sorted(missing)}")
    clean = {key: _bounded(dimensions[key]) for key in adapter.score_weights}
    overall = round(sum(clean[key] * weight for key, weight in adapter.score_weights.items()), 3)
    scores = {**clean, "overall": overall}
    clean_reasons = _clean_reasons(reasons)
    result.metadata.update(
        quality_score_version=adapter.score_version,
        quality_score_weights=dict(adapter.score_weights),
        quality_scores=scores,
        quality_score=overall,
        quality_reasons=clean_reasons,
    )
    return overall, clean_reasons


def apply_quality_metadata(vertical_slug: str, results: list[NameResult], brief: NamingBrief) -> None:
    for result in results:
        score_quality_result(vertical_slug, result, brief)


def evaluate_quality_attributes(
    vertical_slug: str, brief: NamingBrief, results: list[NameResult]
) -> dict[str, float]:
    adapter = quality_adapter_for(vertical_slug)
    if not adapter or not adapter.evaluate_attributes:
        return {}
    return adapter.evaluate_attributes(brief, results)


def quality_model_score_keys(vertical_slug: str, legacy: tuple[str, ...]) -> tuple[str, ...]:
    if not generation_prompt_config_or_none(vertical_slug):
        return legacy
    return generation_model_score_keys(vertical_slug)


def quality_prompt_guidance(vertical_slug: str, legacy: tuple[str, ...]) -> tuple[str, ...]:
    if not generation_prompt_config_or_none(vertical_slug):
        return legacy
    return generation_prompt_guidance(vertical_slug)


def rank_quality_candidates(
    candidates: list[GenerationCandidate], vertical_slug: str | None = None
) -> list[GenerationCandidate]:
    """Rank registered verticals with deterministic ties; preserve legacy ordering otherwise."""
    if quality_adapter_for(vertical_slug or ""):
        return sorted(
            candidates,
            key=lambda candidate: (
                -candidate.quality_score,
                candidate.result.name.casefold(),
                candidate.provider.value,
                candidate.result.slug.casefold(),
                candidate.result.origin.casefold(),
                candidate.result.pronunciation.casefold(),
                candidate.result.tagline.casefold(),
                candidate.result.id,
            ),
        )
    return sorted(candidates, key=lambda candidate: candidate.quality_score, reverse=True)


def explanation_quality_score(result: NameResult, brief: NamingBrief) -> float:
    """Shared check for concise, name- and brief-specific explanations with tradeoffs."""
    explanation = f"{result.why_this_name} {result.fit_note}".lower()
    words = explanation.split()
    brief_words = {
        token.strip(".,;:!?()[]").lower()
        for value in brief.inputs.values()
        for token in str(value).split()
        if len(token.strip(".,;:!?()[]")) > 3
    }
    score = 0.2
    score += 0.2 if result.name.lower() in explanation else 0.0
    score += 0.25 if brief_words & set(explanation.split()) else 0.0
    score += 0.2 if result.risks and ("tradeoff" in explanation or "test" in explanation) else 0.0
    score += 0.15 if 12 <= len(words) <= 100 else 0.0
    return round(min(1.0, score), 3)


def _bounded(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Quality scores must be finite numbers")
    return round(max(0.0, min(1.0, number)), 3)


def _clean_reasons(reasons: list[str]) -> list[str]:
    """Keep adapter-authored metadata bounded and serializable."""
    return [str(reason).strip()[:200] for reason in reasons if str(reason).strip()]
