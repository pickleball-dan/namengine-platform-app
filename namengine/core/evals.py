"""Taste-engine eval fixtures and deterministic regression checks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from namengine.core.briefs import build_brief
from namengine.core.generation import generate_names
from namengine.core.schemas import NameResult, NamingBrief, VerticalConfig

DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "taste_engine_eval_fixtures.json"


@dataclass(slots=True)
class TasteEngineFixture:
    id: str
    label: str
    vertical: str
    inputs: dict[str, Any]
    feelings: dict[str, int] = field(default_factory=dict)
    expected_signals: list[str] = field(default_factory=list)
    contrast_group: str = ""


@dataclass(slots=True)
class TasteEngineEvalResult:
    fixture: TasteEngineFixture
    names: list[NameResult]
    top_names: list[str]
    provider: str
    pipeline: str
    prompt_version: str
    model: str
    signal_hits: list[str]


@dataclass(slots=True)
class TasteEngineContrastResult:
    group: str
    fixture_a: str
    fixture_b: str
    top3_overlap: int
    full_overlap: int
    unique_difference: int
    passed: bool


def load_taste_engine_fixtures(path: Path | str | None = None) -> list[TasteEngineFixture]:
    fixture_path = Path(path) if path else DEFAULT_FIXTURE_PATH
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixtures: list[TasteEngineFixture] = []
    for row in payload:
        fixtures.append(
            TasteEngineFixture(
                id=str(row["id"]),
                label=str(row["label"]),
                vertical=str(row["vertical"]),
                inputs=dict(row.get("inputs", {})),
                feelings={str(key): int(value) for key, value in dict(row.get("feelings", {})).items()},
                expected_signals=[str(item) for item in row.get("expected_signals", [])],
                contrast_group=str(row.get("contrast_group", "")),
            )
        )
    return fixtures


def brief_from_fixture(fixture: TasteEngineFixture) -> NamingBrief:
    from namengine.verticals import get_vertical

    vertical = get_vertical(fixture.vertical)
    source = dict(fixture.inputs)
    source.update(fixture.feelings)
    brief = build_brief(vertical, source)
    _apply_fixture_feelings(brief, fixture.feelings)
    return brief


def run_taste_engine_fixture(
    fixture: TasteEngineFixture,
    use_ai: bool = False,
) -> TasteEngineEvalResult:
    from namengine.verticals import get_vertical

    vertical = get_vertical(fixture.vertical)
    brief = brief_from_fixture(fixture)
    names = generate_names(vertical, brief, use_ai=use_ai)
    top_names = [name.name for name in names]
    metadata = names[0].metadata if names else {}
    provider = str(metadata.get("provider") or metadata.get("source") or "unknown")
    if "fallback" in provider:
        provider = "fallback"
    signal_hits = _signal_hits(fixture, names)
    return TasteEngineEvalResult(
        fixture=fixture,
        names=names,
        top_names=top_names,
        provider=provider,
        pipeline=str(metadata.get("engine_pipeline") or "fallback"),
        prompt_version=str(metadata.get("prompt_version") or "fallback"),
        model=str(metadata.get("model") or "fallback"),
        signal_hits=signal_hits,
    )


def run_taste_engine_fixture_set(
    fixtures: list[TasteEngineFixture] | None = None,
    use_ai: bool = False,
) -> list[TasteEngineEvalResult]:
    return [run_taste_engine_fixture(fixture, use_ai=use_ai) for fixture in (fixtures or load_taste_engine_fixtures())]


def compare_contrast_groups(
    results: list[TasteEngineEvalResult],
    max_top3_overlap: int = 1,
    min_unique_difference: int = 4,
) -> list[TasteEngineContrastResult]:
    by_group: dict[str, list[TasteEngineEvalResult]] = {}
    for result in results:
        if not result.fixture.contrast_group:
            continue
        by_group.setdefault(result.fixture.contrast_group, []).append(result)

    contrasts: list[TasteEngineContrastResult] = []
    for group, group_results in by_group.items():
        for index, left in enumerate(group_results):
            for right in group_results[index + 1 :]:
                left_top3 = set(left.top_names[:3])
                right_top3 = set(right.top_names[:3])
                left_all = set(left.top_names)
                right_all = set(right.top_names)
                top3_overlap = len(left_top3 & right_top3)
                full_overlap = len(left_all & right_all)
                unique_difference = len(left_all ^ right_all)
                contrasts.append(
                    TasteEngineContrastResult(
                        group=group,
                        fixture_a=left.fixture.id,
                        fixture_b=right.fixture.id,
                        top3_overlap=top3_overlap,
                        full_overlap=full_overlap,
                        unique_difference=unique_difference,
                        passed=top3_overlap <= max_top3_overlap and unique_difference >= min_unique_difference,
                    )
                )
    return contrasts


def summarize_taste_engine_eval(results: list[TasteEngineEvalResult]) -> dict[str, Any]:
    contrasts = compare_contrast_groups(results)
    return {
        "fixture_count": len(results),
        "providers": sorted({result.provider for result in results}),
        "pipelines": sorted({result.pipeline for result in results}),
        "contrast_count": len(contrasts),
        "contrast_pass_count": sum(1 for contrast in contrasts if contrast.passed),
        "signal_hit_count": sum(len(result.signal_hits) for result in results),
        "fixtures": [
            {
                "id": result.fixture.id,
                "vertical": result.fixture.vertical,
                "top_names": result.top_names[:8],
                "provider": result.provider,
                "pipeline": result.pipeline,
                "signal_hits": result.signal_hits,
            }
            for result in results
        ],
        "contrasts": [asdict(contrast) for contrast in contrasts],
    }


def _apply_fixture_feelings(brief: NamingBrief, feelings: dict[str, int]) -> None:
    if not feelings:
        return
    clean: dict[str, int] = {}
    for key, value in feelings.items():
        strength = max(0, min(100, int(value)))
        brief.inputs[key] = strength
        if key.startswith("taste_strength_"):
            clean[key[len("taste_strength_") :]] = strength
    if clean:
        strongest = max(clean.items(), key=lambda item: item[1])
        brief.inputs["taste_focus"] = (
            f"Let {strongest[0].replace('_', ' ')} guide this list most while still honoring every intake answer."
        )


def _signal_hits(fixture: TasteEngineFixture, names: list[NameResult]) -> list[str]:
    haystack = " ".join(
        [fixture.label, fixture.vertical]
        + [str(value) for value in fixture.inputs.values()]
        + [
            " ".join(
                [
                    name.name,
                    name.tagline,
                    name.meaning,
                    name.why_this_name,
                    name.fit_note,
                    " ".join(name.tags),
                ]
            )
            for name in names
        ]
    ).lower()
    return [signal for signal in fixture.expected_signals if signal.lower() in haystack]
