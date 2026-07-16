"""Model-provider routing and candidate selection for NamEngine."""

from __future__ import annotations

import time
from collections.abc import Callable

from namengine.core.ai_generation import AIGenerationError, generate_ai_names
import namengine.core.quality_adapters  # Registers built-in vertical adapters.
from namengine.core.quality_framework import rank_quality_candidates, score_quality_result
from namengine.core.generation import generate_fallback_names
from namengine.core.intake import version_metadata_for_brief
from namengine.core.schemas import (
    GenerationCandidate,
    ModelProvider,
    NameResult,
    NamingBrief,
    ProviderResult,
    TasteProfile,
    VerticalConfig,
)


ProviderCallable = Callable[
    [VerticalConfig, NamingBrief, int, TasteProfile | None, list[str]],
    list[NameResult],
]


def generate_with_router(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int = 1,
    taste_profile: TasteProfile | None = None,
    previous_names: list[str] | None = None,
    providers: list[ModelProvider] | None = None,
    count: int | None = None,
) -> list[NameResult]:
    provider_results = route_generation(
        vertical=vertical,
        brief=brief,
        round_number=round_number,
        taste_profile=taste_profile,
        previous_names=previous_names or [],
        providers=providers,
    )
    candidates = score_provider_results(provider_results, brief=brief, vertical=vertical)
    selected = select_best_candidates(
        candidates,
        count=count or _count_for_round(vertical, round_number),
        previous_names=previous_names or [],
        allow_previous_fill=vertical.slug != "baby" and round_number < 4,
        vertical_slug=vertical.slug,
    )
    results = [candidate.result for candidate in selected]
    intake_metadata = version_metadata_for_brief(brief)
    for result in results:
        result.metadata.update(intake_metadata)
    return results


def route_generation(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_profile: TasteProfile | None,
    previous_names: list[str],
    providers: list[ModelProvider] | None = None,
) -> list[ProviderResult]:
    selected_providers = providers or [ModelProvider.OPENAI, ModelProvider.FALLBACK]
    results: list[ProviderResult] = []
    for provider in selected_providers:
        results.append(
            _run_provider(
                provider=provider,
                vertical=vertical,
                brief=brief,
                round_number=round_number,
                taste_profile=taste_profile,
                previous_names=previous_names,
            )
        )
    return results


def score_provider_results(
    provider_results: list[ProviderResult],
    brief: NamingBrief | None = None,
    vertical: VerticalConfig | None = None,
) -> list[GenerationCandidate]:
    candidates: list[GenerationCandidate] = []
    for provider_result in provider_results:
        if provider_result.status != "ok":
            continue
        for result in provider_result.names:
            score, reasons = score_name_result(
                result,
                provider_result.provider,
                brief=brief,
                vertical=vertical,
            )
            result.metadata["provider"] = provider_result.provider.value
            result.metadata.setdefault("source", provider_result.provider.value)
            result.metadata["quality_reasons"] = reasons
            candidates.append(
                GenerationCandidate(
                    result=result,
                    provider=provider_result.provider,
                    quality_score=score,
                    reasons=reasons,
                )
            )
    return candidates


def score_name_result(
    result: NameResult,
    provider: ModelProvider,
    brief: NamingBrief | None = None,
    vertical: VerticalConfig | None = None,
) -> tuple[float, list[str]]:
    vertical_slug = vertical.slug if vertical else (brief.vertical if brief else "")
    quality_score = score_quality_result(vertical_slug, result, brief) if brief else None
    if quality_score is not None:
        return quality_score

    reasons: list[str] = []
    score = 0.0

    callability = float(result.scores.get("callability", 0.0))
    warmth = float(result.scores.get("warmth", 0.0))
    distinctiveness = float(result.scores.get("distinctiveness", 0.0))
    score += callability * 0.35
    score += warmth * 0.25
    score += distinctiveness * 0.2
    if callability >= 0.85:
        reasons.append("high callability")
    if warmth >= 0.85:
        reasons.append("strong warmth")
    if distinctiveness >= 0.75:
        reasons.append("distinctive enough")

    if result.why_this_name and result.fit_note:
        score += 0.1
        reasons.append("complete rationale")
    if result.risks:
        score += 0.05
    if provider != ModelProvider.FALLBACK:
        score += 0.05
        reasons.append(f"{provider.value} candidate")

    return round(min(score, 1.0), 3), reasons


def select_best_candidates(
    candidates: list[GenerationCandidate],
    count: int,
    previous_names: list[str] | None = None,
    allow_previous_fill: bool = True,
    vertical_slug: str | None = None,
) -> list[GenerationCandidate]:
    previous = {name.lower() for name in (previous_names or [])}
    seen: set[str] = set()
    selected: list[GenerationCandidate] = []
    ranked = rank_quality_candidates(candidates, vertical_slug)
    for candidate in ranked:
        key = candidate.result.name.lower()
        if key in seen or key in previous:
            continue
        seen.add(key)
        _stamp_candidate_metadata(candidate)
        selected.append(candidate)
        if len(selected) >= count:
            break

    if allow_previous_fill and len(selected) < count:
        for candidate in ranked:
            key = candidate.result.name.lower()
            if key in seen:
                continue
            seen.add(key)
            _stamp_candidate_metadata(candidate)
            selected.append(candidate)
            if len(selected) >= count:
                break
    return selected


def _stamp_candidate_metadata(candidate: GenerationCandidate) -> None:
    candidate.result.metadata["provider"] = candidate.provider.value
    candidate.result.metadata["quality_score"] = candidate.quality_score
    candidate.result.metadata["quality_reasons"] = candidate.reasons


def _run_provider(
    provider: ModelProvider,
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_profile: TasteProfile | None,
    previous_names: list[str],
) -> ProviderResult:
    start = time.perf_counter()
    try:
        names = _provider_callable(provider)(
            vertical,
            brief,
            round_number,
            taste_profile,
            previous_names,
        )
        return ProviderResult(
            provider=provider,
            names=names,
            latency_ms=_latency_ms(start),
        )
    except Exception as exc:
        return ProviderResult(
            provider=provider,
            status="error",
            error=str(exc),
            latency_ms=_latency_ms(start),
        )


def _provider_callable(provider: ModelProvider) -> ProviderCallable:
    if provider == ModelProvider.OPENAI:
        return _openai_provider
    if provider == ModelProvider.FALLBACK:
        return _fallback_provider
    return _unconfigured_provider(provider)


def _openai_provider(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_profile: TasteProfile | None,
    previous_names: list[str],
) -> list[NameResult]:
    return generate_ai_names(
        vertical=vertical,
        brief=brief,
        round_number=round_number,
        taste_profile=taste_profile,
        previous_names=previous_names,
    )


def _fallback_provider(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_profile: TasteProfile | None,
    previous_names: list[str],
) -> list[NameResult]:
    taste_summary = taste_profile.summary if taste_profile else ""
    return generate_fallback_names(
        vertical=vertical,
        brief=brief,
        round_number=round_number,
        taste_summary=taste_summary,
        previous_names=previous_names,
    )


def _unconfigured_provider(provider: ModelProvider) -> ProviderCallable:
    def call_provider(
        vertical: VerticalConfig,
        brief: NamingBrief,
        round_number: int,
        taste_profile: TasteProfile | None,
        previous_names: list[str],
    ) -> list[NameResult]:
        raise AIGenerationError(f"{provider.value} provider is not configured yet")

    return call_provider


def _count_for_round(vertical: VerticalConfig, round_number: int) -> int:
    if round_number >= 3:
        return 6
    return vertical.default_result_count


def _latency_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)
