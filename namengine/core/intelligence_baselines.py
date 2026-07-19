"""File-backed, synthetic-only baselines for Baby Intelligence."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from namengine.core.intelligence_comparison import (
    BabyIntelligenceComparison,
    compare_baby_intelligence_runs,
)
from namengine.core.intelligence_runs import BabyIntelligenceRun, intelligence_run_from_dict
from namengine.core.schemas import utc_now_iso


BABY_INTELLIGENCE_BASELINE_SCHEMA_VERSION = "baby-intelligence-baseline-v1"
MAX_BASELINE_BYTES = 2_000_000


@dataclass(frozen=True, slots=True)
class BabyIntelligenceBaseline:
    baseline_id: str
    baseline_schema_version: str
    created_at: str
    run: BabyIntelligenceRun
    report_summary: dict[str, Any]

    def __post_init__(self) -> None:
        if self.baseline_schema_version != BABY_INTELLIGENCE_BASELINE_SCHEMA_VERSION:
            raise ValueError("Unsupported Baby Intelligence baseline schema")
        if not self.baseline_id.strip() or self.run.vertical != "baby":
            raise ValueError("Invalid Baby Intelligence baseline identity")
        _validate_report_summary(self.report_summary)

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "baseline_schema_version": self.baseline_schema_version,
            "created_at": self.created_at,
            "run": self.run.to_dict(),
            "report_summary": self.report_summary,
        }

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def create_baby_intelligence_baseline(
    run: BabyIntelligenceRun,
    *,
    baseline_id: str = "baby-intelligence-baseline-v1",
    created_at: str | None = None,
) -> BabyIntelligenceBaseline:
    if run.regression_status == "execution_failure":
        raise ValueError("Cannot baseline an execution failure")
    return BabyIntelligenceBaseline(
        baseline_id=baseline_id.strip(),
        baseline_schema_version=BABY_INTELLIGENCE_BASELINE_SCHEMA_VERSION,
        created_at=created_at or utc_now_iso(),
        run=run,
        report_summary=build_baby_intelligence_baseline_report(run),
    )


def save_baby_intelligence_baseline(
    baseline: BabyIntelligenceBaseline, path: Path | str
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(baseline.serialize() + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def load_baby_intelligence_baseline(path: Path | str) -> BabyIntelligenceBaseline:
    target = Path(path)
    try:
        if target.stat().st_size > MAX_BASELINE_BYTES:
            raise ValueError("Baby Intelligence baseline exceeds its size limit")
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Baby Intelligence baseline is missing or corrupt") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "baseline_id", "baseline_schema_version", "created_at", "run", "report_summary"
    }:
        raise ValueError("Baby Intelligence baseline has an invalid structure")
    _reject_private_data(payload)
    try:
        return BabyIntelligenceBaseline(
            baseline_id=str(payload["baseline_id"]),
            baseline_schema_version=str(payload["baseline_schema_version"]),
            created_at=str(payload["created_at"]),
            run=intelligence_run_from_dict(payload["run"]),
            report_summary=dict(payload["report_summary"]),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Baby Intelligence baseline is invalid") from exc


def compare_with_baby_intelligence_baseline(
    baseline: BabyIntelligenceBaseline,
    current: BabyIntelligenceRun,
) -> BabyIntelligenceComparison:
    comparison = compare_baby_intelligence_runs(baseline.run, current)
    strict_fields = (
        "intake_schema_version", "normalizer_version", "intake_adapter_version",
        "canonical_intent_version", "prompt_version", "quality_adapter_version",
        "evaluation_adapter_version", "model", "provider", "generation_mode",
    )
    differences = tuple(
        f"Baseline configuration differs: {field}"
        for field in strict_fields
        if getattr(baseline.run, field) != getattr(current, field)
    )
    if differences:
        return replace(
            comparison,
            compatible=False,
            compatibility_warnings=tuple(sorted(set(comparison.compatibility_warnings + differences))),
            verdict="incompatible_comparison",
        )
    return comparison


def build_baby_intelligence_baseline_report(run: BabyIntelligenceRun) -> dict[str, Any]:
    ordered = sorted(run.fixture_results, key=lambda item: (-item.normalized_score, item.fixture_id))
    diversity = [item.diversity.score for item in run.fixture_results if item.diversity.score is not None]
    return {
        "overall_score": run.normalized_score,
        "fixture_pass_rate": run.pass_rate,
        "strongest_fixtures": [item.fixture_id for item in ordered[:3]],
        "weakest_fixtures": [item.fixture_id for item in reversed(ordered[-3:])],
        "frequent_weaknesses": [item.code for item in run.weaknesses[:5]],
        "average_diversity_score": round(sum(diversity) / len(diversity), 3) if diversity else None,
        "diversity_limitations": [
            "Naming-territory concentration was not measurable"
        ] if any(item.diversity.territory_concentration is None for item in run.fixture_results) else [],
        "fallback_fixture_count": sum(item.fallback_used for item in run.fixture_results),
        "known_issues": [],
        "versions": {
            "prompt_version": run.prompt_version,
            "intake_schema_version": run.intake_schema_version,
            "canonical_intent_version": run.canonical_intent_version,
            "quality_adapter": run.quality_adapter_version,
            "evaluation_pack": run.fixture_pack_version,
            "provider": run.provider,
            "model": run.model,
        },
        "recommended_engineering_targets": [
            item.suggested_engineering_target for item in run.weaknesses[:5]
        ],
    }


def _reject_private_data(value: Any, path: str = "$", depth: int = 0) -> None:
    if depth > 15:
        raise ValueError("Baseline nesting exceeds its limit")
    blocked = {
        "raw_intake", "canonical_intent", "customer_intake", "prompt", "hidden_prompt",
        "api_key", "authorization", "password", "secret", "stack_trace", "traceback",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).casefold()
            if normalized in blocked or normalized.endswith(("_secret", "_token", "_key")):
                raise ValueError(f"Baseline contains prohibited data at {path}.{key}")
            _reject_private_data(item, f"{path}.{key}", depth + 1)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_private_data(item, f"{path}[{index}]", depth + 1)


def _validate_report_summary(value: Any, depth: int = 0) -> None:
    if depth > 10:
        raise ValueError("Baseline report nesting exceeds its limit")
    if isinstance(value, dict):
        if len(value) > 100:
            raise ValueError("Baseline report contains too many fields")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 100:
                raise ValueError("Baseline report field is invalid")
            _validate_report_summary(item, depth + 1)
    elif isinstance(value, list):
        if len(value) > 100:
            raise ValueError("Baseline report collection exceeds its limit")
        for item in value:
            _validate_report_summary(item, depth + 1)
    elif isinstance(value, str):
        if len(value) > 500:
            raise ValueError("Baseline report text exceeds its limit")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Baseline report numbers must be finite")
    elif value is not None and not isinstance(value, (str, bool, int, float)):
        raise ValueError("Baseline report must be JSON-safe")
