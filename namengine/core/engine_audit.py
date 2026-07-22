"""Engine audit harness for NamEngine taste-discovery regression checks.

The harness is intentionally sheet-first: every audit row maps cleanly to one
Google Sheets row so human/model judges can review the engine without reading
code or Flask templates.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from namengine.core.briefs import build_brief
from namengine.core.evals import TasteEngineFixture, load_taste_engine_fixtures
from namengine.core.generation import generate_names
from namengine.core.schemas import NameResult
from namengine.verticals import get_vertical


DEFAULT_AUDIT_ROUNDS = 4
DEFAULT_MAX_PREVIOUS_OVERLAP_PCT = 0.30
DEFAULT_MIN_SIGNAL_HITS = 2


ROUND_GOALS = {
    1: "best-guess discovery",
    2: "nearby alternatives",
    3: "wider but still relevant",
    4: "hidden gems / final exploration",
}

LANE_PLANS = {
    "baby": {
        1: ("core fit", "Highest-confidence names that honor the stated family, style, sound, and cultural brief."),
        2: ("adjacent style", "Fresh names in a nearby style lane so the user can compare softer, stronger, rarer, or more familiar edges."),
        3: ("wider discovery", "Less obvious names that still stay on-brief and help reveal the user's true taste lane."),
        4: ("hidden gems", "Deeper-cut names with enough fit to be useful, not random novelty."),
    },
    "pet": {
        1: ("callable core", "High-confidence pet-ready names with strong everyday callability and warmth."),
        2: ("personality adjacent", "Fresh names that explore nearby personality and vibe cues without losing usability."),
        3: ("distinctive fit", "More distinctive names that still match the pet type, style, and practical callability needs."),
        4: ("playful hidden gems", "Livelier or more original pet names that remain easy enough to use daily."),
    },
    "business": {
        1: ("positioning core", "Highest-confidence brand names that fit the audience, category, and launch position."),
        2: ("brand-shape alternatives", "Fresh names that test nearby shapes such as compound, evocative, premium, clear, or ownable."),
        3: ("launch-ready names", "Sharper names with practical brand, domain, and positioning discipline."),
        4: ("wider ownable territory", "Broader names that search for more ownable territory while staying commercially credible."),
    },
}


SHEET_COLUMNS = [
    "run_id",
    "fixture_id",
    "label",
    "vertical",
    "round_number",
    "round_goal",
    "lane_label",
    "lane_description",
    "passed",
    "pass_variety",
    "pass_intent",
    "pass_constraints",
    "score",
    "previous_overlap_pct",
    "previous_overlap_count",
    "cumulative_repeat_count",
    "signal_hit_count",
    "signal_hits",
    "constraint_violations",
    "provider",
    "pipeline",
    "model",
    "top_names",
    "name_count",
    "lane_summary",
    "review_question",
    "judge_score",
    "judge_on_brief_1_5",
    "judge_name_quality_1_5",
    "judge_lane_discovery_1_5",
    "judge_would_save_any",
    "judge_names_to_cut",
    "judge_notes",
    "action_needed",
    "brief_json",
]


@dataclass(slots=True)
class EngineAuditRow:
    run_id: str
    fixture_id: str
    label: str
    vertical: str
    round_number: int
    round_goal: str
    lane_label: str
    lane_description: str
    names: list[str]
    previous_overlap_count: int
    previous_overlap_pct: float
    cumulative_repeat_count: int
    signal_hits: list[str]
    constraint_violations: list[str]
    provider: str
    pipeline: str
    model: str
    lane_summary: str
    brief: dict[str, Any]
    pass_variety: bool
    pass_intent: bool
    pass_constraints: bool

    @property
    def passed(self) -> bool:
        return self.pass_variety and self.pass_intent and self.pass_constraints

    @property
    def score(self) -> int:
        score = 0
        if self.pass_variety:
            score += 40
        if self.pass_intent:
            score += 40
        if self.pass_constraints:
            score += 20
        return score

    @property
    def review_question(self) -> str:
        return (
            "Score this round as an independent reviewer: Are the names on-brief, high quality, "
            "and useful for the stated lane? Mark any names to cut and note whether this round helps discover taste."
        )

    def to_sheet_row(self) -> dict[str, Any]:

        return {
            "run_id": self.run_id,
            "fixture_id": self.fixture_id,
            "label": self.label,
            "vertical": self.vertical,
            "round_number": self.round_number,
            "round_goal": self.round_goal,
            "lane_label": self.lane_label,
            "lane_description": self.lane_description,
            "passed": self.passed,
            "pass_variety": self.pass_variety,
            "pass_intent": self.pass_intent,
            "pass_constraints": self.pass_constraints,
            "score": self.score,
            "previous_overlap_pct": round(self.previous_overlap_pct, 3),
            "previous_overlap_count": self.previous_overlap_count,
            "cumulative_repeat_count": self.cumulative_repeat_count,
            "signal_hit_count": len(self.signal_hits),
            "signal_hits": " | ".join(self.signal_hits),
            "constraint_violations": " | ".join(self.constraint_violations),
            "provider": self.provider,
            "pipeline": self.pipeline,
            "model": self.model,
            "top_names": " | ".join(self.names),
            "name_count": len(self.names),
            "lane_label": self.lane_label,
            "lane_description": self.lane_description,
            "lane_summary": self.lane_summary,
            "review_question": self.review_question,
            # Blank columns are deliberate: paste/import into Google Sheets, then
            # use these for independent human/model review without altering data.
            "judge_score": "",
            "judge_on_brief_1_5": "",
            "judge_name_quality_1_5": "",
            "judge_lane_discovery_1_5": "",
            "judge_would_save_any": "",
            "judge_names_to_cut": "",
            "judge_notes": "",
            "action_needed": "",
            "brief_json": json.dumps(self.brief, ensure_ascii=False, sort_keys=True),
        }


def make_audit_run_id() -> str:
    return datetime.now(timezone.utc).strftime("engine-audit-%Y%m%d-%H%M%S")


def run_engine_audit(
    fixtures: list[TasteEngineFixture] | None = None,
    *,
    rounds: int = DEFAULT_AUDIT_ROUNDS,
    use_ai: bool = False,
    max_previous_overlap_pct: float = DEFAULT_MAX_PREVIOUS_OVERLAP_PCT,
    min_signal_hits: int = DEFAULT_MIN_SIGNAL_HITS,
    run_id: str | None = None,
) -> list[EngineAuditRow]:
    """Run lane-discovery checks across fixtures and consecutive rounds.

    Each fixture simulates a user repeatedly asking for a fresh round without
    changing the original brief. Previous names are passed forward so the engine
    is expected to explore adjacent lanes instead of repeating the same slate.
    """
    audit_run_id = run_id or make_audit_run_id()
    rows: list[EngineAuditRow] = []
    for fixture in fixtures or load_taste_engine_fixtures():
        rows.extend(
            run_fixture_audit(
                fixture,
                rounds=rounds,
                use_ai=use_ai,
                max_previous_overlap_pct=max_previous_overlap_pct,
                min_signal_hits=min_signal_hits,
                run_id=audit_run_id,
            )
        )
    return rows


def run_fixture_audit(
    fixture: TasteEngineFixture,
    *,
    rounds: int = DEFAULT_AUDIT_ROUNDS,
    use_ai: bool = False,
    max_previous_overlap_pct: float = DEFAULT_MAX_PREVIOUS_OVERLAP_PCT,
    min_signal_hits: int = DEFAULT_MIN_SIGNAL_HITS,
    run_id: str | None = None,
) -> list[EngineAuditRow]:
    vertical = get_vertical(fixture.vertical)
    source = dict(fixture.inputs)
    source.update(fixture.feelings)
    brief = build_brief(vertical, source)
    audit_run_id = run_id or make_audit_run_id()

    rows: list[EngineAuditRow] = []
    previous_round_names: list[str] = []
    cumulative_names: list[str] = []
    for round_number in range(1, rounds + 1):
        results = generate_names(
            vertical,
            brief,
            round_number=round_number,
            previous_names=cumulative_names,
            use_ai=use_ai,
        )
        names = [result.name for result in results]
        previous_overlap = _name_overlap(names, previous_round_names)
        cumulative_repeats = _name_overlap(names, cumulative_names)
        overlap_pct = previous_overlap / max(1, len(names))
        signal_hits = _signal_hits(fixture, results)
        violations = _constraint_violations(brief_avoid=brief.avoid, names=names)
        metadata = results[0].metadata if results else {}
        pass_variety = round_number == 1 or overlap_pct <= max_previous_overlap_pct
        pass_intent = len(signal_hits) >= min(min_signal_hits, len(fixture.expected_signals))
        pass_constraints = not violations
        rows.append(
            EngineAuditRow(
                run_id=audit_run_id,
                fixture_id=fixture.id,
                label=fixture.label,
                vertical=fixture.vertical,
                round_number=round_number,
                round_goal=ROUND_GOALS.get(round_number, "fresh exploration"),
                lane_label=lane_for_fixture(fixture, round_number)[0],
                lane_description=lane_for_fixture(fixture, round_number)[1],
                names=names,
                previous_overlap_count=previous_overlap,
                previous_overlap_pct=overlap_pct,
                cumulative_repeat_count=cumulative_repeats,
                signal_hits=signal_hits,
                constraint_violations=violations,
                provider=str(metadata.get("provider") or metadata.get("source") or "unknown"),
                pipeline=str(metadata.get("engine_pipeline") or "fallback"),
                model=str(metadata.get("model") or "fallback"),
                lane_summary=_lane_summary(results),
                brief={
                    "inputs": brief.inputs,
                    "avoid": brief.avoid,
                    "notes": brief.notes,
                    "liked_examples": brief.liked_examples,
                    "rejected_examples": brief.rejected_examples,
                },
                pass_variety=pass_variety,
                pass_intent=pass_intent,
                pass_constraints=pass_constraints,
            )
        )
        previous_round_names = names
        cumulative_names.extend(names)
    return rows


def write_engine_audit_csv(rows: list[EngineAuditRow], path: Path | str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_sheet_row())
    return output_path


def write_engine_audit_json(rows: list[EngineAuditRow], path: Path | str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(row) | {"passed": row.passed, "score": row.score} for row in rows]
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def summarize_engine_audit(rows: list[EngineAuditRow]) -> dict[str, Any]:
    fixture_ids = {row.fixture_id for row in rows}
    failed = [row for row in rows if not row.passed]
    return {
        "row_count": len(rows),
        "fixture_count": len(fixture_ids),
        "round_count": max([row.round_number for row in rows], default=0),
        "passed_count": sum(1 for row in rows if row.passed),
        "failed_count": len(failed),
        "average_score": round(sum(row.score for row in rows) / max(1, len(rows)), 1),
        "failed_rows": [
            {
                "fixture_id": row.fixture_id,
                "round_number": row.round_number,
                "score": row.score,
                "names": row.names,
                "signal_hits": row.signal_hits,
                "constraint_violations": row.constraint_violations,
                "previous_overlap_pct": round(row.previous_overlap_pct, 3),
            }
            for row in failed
        ],
    }


def lane_for_fixture(fixture: TasteEngineFixture, round_number: int) -> tuple[str, str]:
    """Return the intended discovery lane for a fixture/round.

    This is deliberately human-readable: it lets the CSV prove that a new round
    is exploring a different angle, not merely reshuffling names.
    """
    vertical_plan = LANE_PLANS.get(fixture.vertical, {})
    label, description = vertical_plan.get(
        round_number,
        ("fresh exploration", "Another fresh, on-brief naming angle with low repetition."),
    )
    expected = {signal.lower() for signal in fixture.expected_signals}
    if fixture.vertical == "baby" and expected & {"heritage", "cultural", "italian", "irish", "scandinavian"}:
        if round_number in {2, 3}:
            return (
                "heritage-adjacent discovery",
                "Fresh names that test adjacent heritage, family, and style cues while staying respectful and on-brief.",
            )
    return label, description


def _name_overlap(left: list[str], right: list[str]) -> int:
    return len({_clean_name(name) for name in left} & {_clean_name(name) for name in right})


def _clean_name(name: str) -> str:
    return "".join(character for character in name.lower() if character.isalnum())


def _signal_hits(fixture: TasteEngineFixture, results: list[NameResult]) -> list[str]:
    haystack = " ".join(
        [fixture.label, fixture.vertical]
        + [str(value) for value in fixture.inputs.values()]
        + [
            " ".join(
                [
                    result.name,
                    result.tagline,
                    result.meaning,
                    result.why_this_name,
                    result.fit_note,
                    " ".join(result.tags),
                    " ".join(result.risks),
                ]
            )
            for result in results
        ]
    ).lower()
    return [signal for signal in fixture.expected_signals if signal.lower() in haystack]


def _constraint_violations(*, brief_avoid: list[str], names: list[str]) -> list[str]:
    avoid = {_clean_name(item) for item in brief_avoid if item}
    if not avoid:
        return []
    return [f"avoid-list repeat: {name}" for name in names if _clean_name(name) in avoid]


def _lane_summary(results: list[NameResult]) -> str:
    tag_counts: dict[str, int] = {}
    for result in results:
        for tag in result.tags[:5]:
            clean = str(tag).strip().lower()
            if not clean:
                continue
            tag_counts[clean] = tag_counts.get(clean, 0) + 1
    if not tag_counts:
        return ""
    ranked = sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
    return " | ".join(f"{tag}:{count}" for tag, count in ranked)
