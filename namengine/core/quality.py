"""Quality harness for scoring NamEngine generation runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from namengine.core.briefs import build_brief
from namengine.core.model_router import (
    route_generation,
    score_provider_results,
    select_best_candidates,
)
from namengine.core.schemas import (
    GenerationCandidate,
    ModelProvider,
    NamingBrief,
    ProviderResult,
    VerticalConfig,
)


@dataclass(slots=True)
class QualityBrief:
    id: str
    vertical: str
    inputs: dict[str, Any]
    must_avoid: list[str] = field(default_factory=list)
    desired_traits: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(slots=True)
class QualityRunResult:
    brief_id: str
    provider_results: list[ProviderResult]
    selected: list[GenerationCandidate]
    average_score: float
    duplicate_count: int
    avoided_name_hits: int


def load_quality_briefs(path: Path) -> list[QualityBrief]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        QualityBrief(
            id=str(row["id"]),
            vertical=str(row["vertical"]),
            inputs=dict(row.get("inputs", {})),
            must_avoid=[str(item) for item in row.get("must_avoid", [])],
            desired_traits=[str(item) for item in row.get("desired_traits", [])],
            notes=str(row.get("notes", "")),
        )
        for row in payload
    ]


def run_quality_brief(
    quality_brief: QualityBrief,
    vertical: VerticalConfig,
    providers: list[ModelProvider] | None = None,
    round_number: int = 1,
) -> QualityRunResult:
    brief = _to_naming_brief(quality_brief, vertical)
    provider_results = route_generation(
        vertical=vertical,
        brief=brief,
        round_number=round_number,
        taste_profile=None,
        previous_names=[],
        providers=providers or [ModelProvider.OPENAI, ModelProvider.FALLBACK],
    )
    candidates = score_provider_results(provider_results, brief=brief, vertical=vertical)
    selected = select_best_candidates(
        candidates,
        count=vertical.default_result_count if round_number < 3 else 6,
        vertical_slug=vertical.slug,
    )
    return QualityRunResult(
        brief_id=quality_brief.id,
        provider_results=provider_results,
        selected=selected,
        average_score=_average_score(selected),
        duplicate_count=_duplicate_count(candidates),
        avoided_name_hits=_avoided_name_hits(candidates, quality_brief.must_avoid),
    )


def summarize_quality_runs(runs: list[QualityRunResult]) -> dict[str, Any]:
    provider_status: dict[str, dict[str, int]] = {}
    for run in runs:
        for result in run.provider_results:
            bucket = provider_status.setdefault(result.provider.value, {"ok": 0, "error": 0})
            bucket[result.status] = bucket.get(result.status, 0) + 1

    return {
        "brief_count": len(runs),
        "average_score": round(
            sum(run.average_score for run in runs) / len(runs),
            3,
        )
        if runs
        else 0.0,
        "duplicate_count": sum(run.duplicate_count for run in runs),
        "avoided_name_hits": sum(run.avoided_name_hits for run in runs),
        "provider_status": provider_status,
    }


def _to_naming_brief(
    quality_brief: QualityBrief,
    vertical: VerticalConfig,
) -> NamingBrief:
    source = dict(quality_brief.inputs)
    if quality_brief.must_avoid:
        source["avoid"] = ", ".join(quality_brief.must_avoid)
    brief = build_brief(vertical, source)
    brief.notes = quality_brief.notes
    return brief


def _average_score(candidates: list[GenerationCandidate]) -> float:
    if not candidates:
        return 0.0
    return round(
        sum(candidate.quality_score for candidate in candidates) / len(candidates),
        3,
    )


def _duplicate_count(candidates: list[GenerationCandidate]) -> int:
    names = [candidate.result.name.lower() for candidate in candidates]
    return len(names) - len(set(names))


def _avoided_name_hits(
    candidates: list[GenerationCandidate],
    must_avoid: list[str],
) -> int:
    avoid = {name.lower() for name in must_avoid}
    return sum(1 for candidate in candidates if candidate.result.name.lower() in avoid)
