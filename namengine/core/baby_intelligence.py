"""Baby Intelligence runner, Baby-owned metrics, diversity, and weaknesses."""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from namengine.core.baby_evaluation_adapter import BABY_EVALUATION_ADAPTER_VERSION
from namengine.core.baby_intake_adapter import (
    BABY_INTAKE_ADAPTER_VERSION,
    BABY_INTAKE_VERSION,
    BABY_NORMALIZER_VERSION,
)
from namengine.core.baby_quality_adapter import BABY_QUALITY_SCORE_VERSION
from namengine.core.baby_intelligence_metrics import (
    analyze_baby_candidate_diversity,
    analyze_baby_weaknesses,
    build_candidate_diagnostics,
    calculate_baby_intelligence_metrics,
    summarize_baby_metrics,
    unavailable_baby_metrics,
)
from namengine.core.briefs import build_brief
from namengine.core.canonical_intent import CANONICAL_INTENT_VERSION
from namengine.core.generation import generate_names
from namengine.core.intelligence_runs import (
    INTELLIGENCE_RUN_SCHEMA_VERSION,
    BabyIntelligenceRun,
    DiversityAnalysis,
    FixtureIntelligenceResult,
)
from namengine.core.name_evaluation import (
    DEFAULT_PACK_ROOT,
    NameEvaluationFixture,
    evaluate_fixture,
    load_evaluation_pack,
)
from namengine.core.prompt_versions import prompt_version_for, registered_prompt_versions
from namengine.core.quality_framework import apply_quality_metadata, quality_adapter_for
from namengine.core.schemas import ModelProvider, NameResult, NamingBrief, utc_now_iso
from namengine.verticals import BABY


BABY_INTELLIGENCE_VERSION = "baby-intelligence-v1"
BABY_EVALUATION_PACK_VERSION = "baby-evaluation-pack-v1"
DEFAULT_BABY_PACK = DEFAULT_PACK_ROOT / "baby"
MAX_FIXTURE_RUNS = 100

GenerationCallable = Callable[[Any, NamingBrief, "BabyIntelligenceConfig"], list[NameResult]]


@dataclass(frozen=True, slots=True)
class BabyIntelligenceConfig:
    fixture_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    prompt_version: str = ""
    intake_version: str = ""
    quality_adapter_version: str = ""
    evaluation_adapter_version: str = ""
    model: str = ""
    provider: str = "fallback"
    repeat_count: int = 1
    deterministic_seed: int | None = None
    include_fallback: bool = True
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not 1 <= self.repeat_count <= 10:
            raise ValueError("Repeat count must be between 1 and 10")
        if not 0 < self.timeout_seconds <= 300:
            raise ValueError("Timeout must be between 0 and 300 seconds")
        if self.provider not in {"fallback", "openai", "auto"}:
            raise ValueError("Unsupported Baby Intelligence provider")
        if self.provider == "fallback" and not self.include_fallback:
            raise ValueError("Fallback provider cannot be excluded when it is the selected provider")


def run_baby_intelligence(
    config: BabyIntelligenceConfig | None = None,
    *,
    pack_path=DEFAULT_BABY_PACK,
    generation_callable: GenerationCallable | None = None,
) -> BabyIntelligenceRun:
    """Execute enabled Baby fixtures through the real pipeline and evaluator."""
    selected = config or BabyIntelligenceConfig()
    _validate_versions(selected)
    fixtures = load_evaluation_pack(
        pack_path,
        vertical="baby",
        tags=set(selected.tags) if selected.tags else None,
    )
    if selected.fixture_ids:
        requested = set(selected.fixture_ids)
        fixtures = [fixture for fixture in fixtures if fixture.fixture_id in requested]
        missing = sorted(requested - {fixture.fixture_id for fixture in fixtures})
        if missing:
            raise ValueError(f"Unknown or disabled Baby fixture IDs: {missing}")
    fixtures = sorted(fixtures, key=lambda fixture: fixture.fixture_id)
    if not fixtures:
        raise ValueError("Baby Intelligence selected no enabled fixtures")
    if len(fixtures) * selected.repeat_count > MAX_FIXTURE_RUNS:
        raise ValueError("Baby Intelligence run exceeds fixture execution limit")

    started_at = utc_now_iso()
    generator = generation_callable or _generate_for_config
    fixture_results: list[FixtureIntelligenceResult] = []
    diagnostics: list[str] = []
    if selected.deterministic_seed is not None:
        diagnostics.append(
            "Deterministic seed recorded; the current generation provider does not expose seed control"
        )
    for fixture in fixtures:
        for repeat_index in range(1, selected.repeat_count + 1):
            fixture_results.append(
                _run_fixture(fixture, repeat_index, selected, generator)
            )
    actual_model = _dominant(item.model for item in fixture_results)
    if selected.model and selected.model != actual_model:
        diagnostics.append("Requested model did not match the model reported by generation")

    aggregate = round(sum(item.total_score for item in fixture_results), 3)
    maximum = round(sum(item.maximum_score for item in fixture_results), 3)
    normalized = round(aggregate / maximum, 3) if maximum else 0.0
    pass_rate = round(sum(item.passed for item in fixture_results) / len(fixture_results), 3)
    weaknesses = analyze_baby_weaknesses(tuple(fixture_results))
    metric_summaries = summarize_baby_metrics(fixture_results)
    failure_count = sum(len(item.failure_reasons) + bool(item.execution_error) for item in fixture_results)
    warning_count = sum(len(item.warnings) + item.timeout for item in fixture_results)
    fallback_count = sum(item.fallback_used for item in fixture_results)
    critical_failure = any(
        row.get("criterion") in {"privacy_safety", "prohibited_names", "prohibited_patterns"}
        and row.get("status") == "fail"
        for fixture in fixture_results
        for row in fixture.criterion_results
    )
    status = "execution_failure" if any(item.execution_error for item in fixture_results) else (
        "regression_detected" if critical_failure else
        "pass_with_warnings" if failure_count or warning_count else "pass"
    )
    completed_at = utc_now_iso()
    run_id = _run_id(started_at, selected, fixture_results)
    return BabyIntelligenceRun(
        run_id=run_id,
        run_schema_version=INTELLIGENCE_RUN_SCHEMA_VERSION,
        started_at=started_at,
        completed_at=completed_at,
        vertical="baby",
        fixture_pack_version=BABY_EVALUATION_PACK_VERSION,
        fixture_ids=tuple(fixture.fixture_id for fixture in fixtures),
        intake_schema_version=selected.intake_version or BABY_INTAKE_VERSION,
        normalizer_version=BABY_NORMALIZER_VERSION,
        intake_adapter_version=BABY_INTAKE_ADAPTER_VERSION,
        canonical_intent_version=CANONICAL_INTENT_VERSION,
        prompt_version=selected.prompt_version or prompt_version_for("baby"),
        quality_adapter_version=selected.quality_adapter_version or BABY_QUALITY_SCORE_VERSION,
        evaluation_adapter_version=selected.evaluation_adapter_version or BABY_EVALUATION_ADAPTER_VERSION,
        model=actual_model,
        provider=selected.provider if selected.provider != "auto" else _dominant(item.provider for item in fixture_results),
        generation_mode="test_double" if generation_callable else selected.provider,
        fallback_status=f"{fallback_count}/{len(fixture_results)} fixture executions used fallback",
        fixture_results=tuple(fixture_results),
        aggregate_score=aggregate,
        maximum_score=maximum,
        normalized_score=normalized,
        pass_rate=pass_rate,
        failure_count=failure_count,
        warning_count=warning_count,
        metric_summaries=metric_summaries,
        weaknesses=weaknesses,
        regression_status=status,
        diagnostics=tuple(diagnostics),
    )


def _run_fixture(
    fixture: NameEvaluationFixture,
    repeat_index: int,
    config: BabyIntelligenceConfig,
    generator: GenerationCallable,
) -> FixtureIntelligenceResult:
    brief = build_brief(BABY, fixture.intake)
    started = time.perf_counter()
    try:
        results = generator(BABY, brief, config)
        if any(not isinstance(item.metadata.get("quality_scores"), dict) for item in results):
            apply_quality_metadata("baby", results, brief)
        elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
        timed_out = elapsed_ms > int(config.timeout_seconds * 1000)
        if timed_out:
            raise TimeoutError("Baby Intelligence generation exceeded its configured timeout")
        comparison = None
        if any(row.criterion == "deterministic_ordering" for row in fixture.criteria):
            comparison = generator(BABY, brief, config)
        evaluated = evaluate_fixture(fixture, results, comparison_results=comparison)
        candidates = build_candidate_diagnostics(fixture, brief, results)
        diversity = analyze_baby_candidate_diversity(results)
        metrics = calculate_baby_intelligence_metrics(brief, results, diversity)
        providers = [
            str(item.metadata.get("provider") or item.metadata.get("source") or "unknown")
            for item in results
        ]
        fallback = any("fallback" in value.casefold() for value in providers)
        latency = _provider_latency(results)
        return FixtureIntelligenceResult(
            fixture_id=fixture.fixture_id,
            repeat_index=repeat_index,
            passed=evaluated.passed,
            total_score=evaluated.total_score,
            maximum_score=evaluated.maximum_score,
            normalized_score=evaluated.normalized_score,
            criterion_results=tuple(item_to_safe_dict(item) for item in evaluated.criterion_results),
            failure_reasons=evaluated.failure_reasons,
            warnings=evaluated.warnings,
            candidates=candidates,
            metrics=metrics,
            diversity=diversity,
            provider=_dominant(providers),
            model=evaluated.model,
            fallback_used=fallback,
            latency_ms=latency if latency is not None else elapsed_ms,
        )
    except TimeoutError:
        elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
        return _execution_failure(fixture.fixture_id, repeat_index, "generation_timeout", elapsed_ms, True)
    except Exception as exc:
        elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
        return _execution_failure(
            fixture.fixture_id,
            repeat_index,
            f"generation_{type(exc).__name__}",
            elapsed_ms,
            False,
        )


def _generate_for_config(vertical, brief: NamingBrief, config: BabyIntelligenceConfig) -> list[NameResult]:
    if config.provider == "fallback":
        return generate_names(vertical, brief, use_ai=False)
    if config.provider in {"openai", "auto"} and not config.include_fallback:
        from namengine.core.model_router import generate_with_router

        return generate_with_router(vertical, brief, providers=[ModelProvider.OPENAI])
    return generate_names(vertical, brief, use_ai=True)


def _execution_failure(fixture_id: str, repeat: int, code: str, latency: int, timeout: bool) -> FixtureIntelligenceResult:
    return FixtureIntelligenceResult(
        fixture_id=fixture_id,
        repeat_index=repeat,
        passed=False,
        total_score=0.0,
        maximum_score=1.0,
        normalized_score=0.0,
        criterion_results=({"criterion": "execution", "status": "fail", "score": 0.0, "maximum_score": 1.0},),
        failure_reasons=("Generation could not be evaluated",),
        warnings=("Generation timed out",) if timeout else (),
        candidates=(),
        metrics=unavailable_baby_metrics("Generation did not complete"),
        diversity=DiversityAnalysis("not_applicable", None, reasons=("Generation did not complete",)),
        provider="unknown",
        model="unknown",
        fallback_used=False,
        latency_ms=latency,
        timeout=timeout,
        execution_error=code[:100],
    )


def _validate_versions(config: BabyIntelligenceConfig) -> None:
    actual_prompt = prompt_version_for("baby")
    if config.prompt_version and config.prompt_version not in registered_prompt_versions().values():
        raise ValueError("Unknown Baby prompt version")
    if config.prompt_version and config.prompt_version != actual_prompt:
        raise ValueError("Requested prompt version is not active for Baby generation")
    if config.intake_version and config.intake_version != BABY_INTAKE_VERSION:
        raise ValueError("Requested Baby intake version is not active")
    adapter = quality_adapter_for("baby")
    actual_quality = adapter.score_version if adapter else ""
    if config.quality_adapter_version and config.quality_adapter_version != actual_quality:
        raise ValueError("Requested Baby quality adapter version is not active")
    if config.evaluation_adapter_version and config.evaluation_adapter_version != BABY_EVALUATION_ADAPTER_VERSION:
        raise ValueError("Requested Baby evaluation adapter version is not active")


def item_to_safe_dict(item) -> dict[str, Any]:
    return {
        "criterion": item.criterion[:100],
        "status": item.status,
        "score": item.score,
        "maximum_score": item.maximum_score,
        "required": item.required,
        "reason": item.reason[:500],
        "details": item.details,
    }


def _provider_latency(results: list[NameResult]) -> int | None:
    total = 0
    found = False
    for result in results[:1]:
        calls = result.metadata.get("ai_calls", [])
        if not isinstance(calls, list):
            continue
        for call in calls:
            if isinstance(call, dict) and isinstance(call.get("latency_ms"), (int, float)):
                total += max(0, int(call["latency_ms"]))
                found = True
    return total if found else None


def _dominant(values) -> str:
    clean = [str(value)[:100] for value in values if str(value).strip()]
    return Counter(clean).most_common(1)[0][0] if clean else "unknown"


def _run_id(started_at: str, config: BabyIntelligenceConfig, results: list[FixtureIntelligenceResult]) -> str:
    payload = {
        "started_at": started_at,
        "config": {
            "fixture_ids": config.fixture_ids,
            "tags": config.tags,
            "provider": config.provider,
            "repeat_count": config.repeat_count,
            "seed": config.deterministic_seed,
        },
        "results": [(item.fixture_id, item.repeat_index, item.normalized_score) for item in results],
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"baby-intelligence-{digest}"
