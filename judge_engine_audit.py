"""Blind/reviewer pass for NamEngine engine-audit CSVs.

This script fills the blank reviewer columns produced by `run_engine_audit.py`.
It supports two modes:

1. Default local judge: deterministic, cheap, conservative smoke filter.
2. Optional AI judge: `--use-ai`, blind model review with no engine-code context.

Usage:
    python judge_engine_audit.py --latest
    python judge_engine_audit.py --latest --use-ai
    python judge_engine_audit.py audit_outputs/engine-audit-YYYYMMDD-HHMMSS.csv --use-ai --limit 10
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Callable
from namengine.core.openai_telemetry import record_openai_telemetry

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

JUDGE_COLUMNS = [
    "judge_score",
    "judge_on_brief_1_5",
    "judge_name_quality_1_5",
    "judge_lane_discovery_1_5",
    "judge_would_save_any",
    "judge_names_to_cut",
    "judge_notes",
    "action_needed",
]

DEFAULT_AI_JUDGE_MODEL = "gpt-4.1-mini"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score a NamEngine audit CSV with a blind judge.")
    parser.add_argument("csv_path", nargs="?", help="Audit CSV to judge.")
    parser.add_argument("--latest", action="store_true", help="Use latest audit_outputs/engine-audit-*.csv file.")
    parser.add_argument("--out", default="", help="Output CSV path. Defaults to *-judged.csv or *-ai-judged.csv.")
    parser.add_argument("--use-ai", action="store_true", help="Use OpenAI blind judge when OPENAI_API_KEY is available.")
    parser.add_argument("--require-ai", action="store_true", help="Fail instead of falling back when AI judge is unavailable.")
    parser.add_argument("--model", default="", help=f"AI judge model. Default: {DEFAULT_AI_JUDGE_MODEL}.")
    parser.add_argument("--limit", type=int, default=0, help="Judge only the first N rows, useful for cost-controlled spot checks.")
    return parser.parse_args()


def latest_audit_csv() -> Path:
    files = sorted(Path("audit_outputs").glob("engine-audit-*.csv"), key=lambda path: path.stat().st_mtime)
    files = [path for path in files if "-judged" not in path.stem]
    if not files:
        raise SystemExit("No audit CSV files found in audit_outputs/.")
    return files[-1]


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    final_fields = list(fieldnames)
    for column in JUDGE_COLUMNS:
        if column not in final_fields:
            final_fields.append(column)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=final_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def judge_rows(
    rows: list[dict[str, str]],
    *,
    use_ai: bool = False,
    require_ai: bool = False,
    model: str = "",
    client_factory: Callable[[], Any] | None = None,
) -> tuple[list[dict[str, str]], str]:
    if not use_ai:
        return [judge_row(dict(row)) for row in rows], "local"

    try:
        judged = [judge_row_with_ai(dict(row), model=model, client_factory=client_factory) for row in rows]
        return judged, "ai"
    except Exception as exc:
        if require_ai:
            raise
        judged = [judge_row(dict(row)) for row in rows]
        for row in judged:
            row["judge_notes"] = f"AI judge unavailable ({type(exc).__name__}); local judge used. " + row.get("judge_notes", "")
            if row.get("action_needed") == "no action":
                row["action_needed"] = "ai judge unavailable"
        return judged, "local_fallback"


def judge_row(row: dict[str, str]) -> dict[str, str]:
    """Deterministic smoke judge.

    This deliberately scores mechanics, not taste. Use AI/human review for real
    taste judgment.
    """
    signal_count = _int(row.get("signal_hit_count"))
    overlap = _float(row.get("previous_overlap_pct"))
    repeats = _int(row.get("cumulative_repeat_count"))
    constraints = row.get("constraint_violations", "").strip()
    names = _split_pipe(row.get("top_names", ""))
    lane_label = row.get("lane_label", "").strip()
    passed = row.get("passed", "").lower() == "true"

    on_brief = 3
    if signal_count >= 4:
        on_brief = 5
    elif signal_count >= 2:
        on_brief = 4
    if constraints:
        on_brief = max(1, on_brief - 2)

    name_quality = 4
    if len(names) >= 6:
        name_quality += 1
    if constraints:
        name_quality -= 2
    if _has_obvious_noise(names):
        name_quality -= 1
    name_quality = _clamp_1_5(name_quality)

    lane_discovery = 3
    if lane_label and overlap <= 0.10:
        lane_discovery = 5
    elif lane_label and overlap <= 0.30:
        lane_discovery = 4
    elif overlap > 0.30:
        lane_discovery = 2
    if repeats and overlap > 0:
        lane_discovery = max(1, lane_discovery - 1)

    return _apply_judgment(row, on_brief, name_quality, lane_discovery, _names_to_cut(row, names), judge_kind="local")


def judge_row_with_ai(
    row: dict[str, str],
    *,
    model: str = "",
    client_factory: Callable[[], Any] | None = None,
) -> dict[str, str]:
    if client_factory is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not configured")
        from openai import OpenAI

        client_factory = OpenAI

    client = client_factory()
    selected_model = model or os.getenv("NAMENGINE_AI_JUDGE_MODEL", DEFAULT_AI_JUDGE_MODEL)
    prompt = build_ai_judge_prompt(row)
    started_at = time.perf_counter()
    try:
        response = client.responses.create(
            model=selected_model,
            input=[
            {
                "role": "system",
                "content": (
                    "You are an independent naming-product QA judge. You are blind to the code. "
                    "Score harshly enough to be useful. Do not reward mechanical pass/fail alone. "
                    "Prefer concise, actionable notes. Return only valid JSON."
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
            response_format=ai_judge_response_format(),
        )
    except Exception as exc:
        record_openai_telemetry(request_type="responses.create", model=selected_model, started_at=started_at, success=False, context="ai_judge", error_type=exc.__class__.__name__)
        raise
    record_openai_telemetry(request_type="responses.create", model=selected_model, started_at=started_at, success=True, usage=getattr(response, "usage", None), context="ai_judge")
    payload = json.loads(response.output_text)
    cuts = [str(item) for item in payload.get("names_to_cut", [])]
    row = _apply_judgment(
        row,
        _clamp_1_5(int(payload.get("on_brief", 3))),
        _clamp_1_5(int(payload.get("name_quality", 3))),
        _clamp_1_5(int(payload.get("lane_discovery", 3))),
        cuts,
        judge_kind="ai",
        notes=str(payload.get("notes", "")).strip(),
        action_needed=str(payload.get("action_needed", "")).strip(),
        would_save=str(payload.get("would_save_any", "")).strip(),
    )
    return row


def build_ai_judge_prompt(row: dict[str, str]) -> dict[str, Any]:
    return {
        "task": "Independently judge this naming-engine audit row.",
        "vertical": row.get("vertical"),
        "fixture_label": row.get("label"),
        "round_number": row.get("round_number"),
        "lane_label": row.get("lane_label"),
        "lane_description": row.get("lane_description"),
        "top_names": _split_pipe(row.get("top_names", "")),
        "brief": _safe_json(row.get("brief_json", "{}")),
        "mechanical_context": {
            "passed_mechanical_gate": row.get("passed"),
            "previous_overlap_pct": row.get("previous_overlap_pct"),
            "signal_hits": row.get("signal_hits"),
            "constraint_violations": row.get("constraint_violations"),
        },
        "scoring": {
            "on_brief": "1 ignored the brief, 3 partly aligned, 5 clearly understood it",
            "name_quality": "1 weak/cringe/unusable, 3 mixed, 5 polished and realistic",
            "lane_discovery": "1 reshuffle/random, 3 somewhat distinct, 5 clearly useful for discovering taste",
        },
        "return_json_only": True,
    }


def ai_judge_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "namengine_audit_judge_v1",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "on_brief",
                "name_quality",
                "lane_discovery",
                "would_save_any",
                "names_to_cut",
                "notes",
                "action_needed",
            ],
            "properties": {
                "on_brief": {"type": "integer", "minimum": 1, "maximum": 5},
                "name_quality": {"type": "integer", "minimum": 1, "maximum": 5},
                "lane_discovery": {"type": "integer", "minimum": 1, "maximum": 5},
                "would_save_any": {"type": "string", "enum": ["Yes", "Maybe", "No"]},
                "names_to_cut": {"type": "array", "items": {"type": "string"}},
                "notes": {"type": "string"},
                "action_needed": {
                    "type": "string",
                    "enum": [
                        "no action",
                        "brief-fit review",
                        "candidate quality review",
                        "lane discovery review",
                        "candidate pool expansion",
                        "human review recommended",
                    ],
                },
            },
        },
    }


def _apply_judgment(
    row: dict[str, str],
    on_brief: int,
    name_quality: int,
    lane_discovery: int,
    names_to_cut: list[str],
    *,
    judge_kind: str,
    notes: str = "",
    action_needed: str = "",
    would_save: str = "",
) -> dict[str, str]:
    scores = [on_brief, name_quality, lane_discovery]
    judge_score = round(mean(scores), 2)
    if not would_save:
        would_save = "Yes" if judge_score >= 4.25 else "Maybe" if judge_score >= 3.25 else "No"
    if not action_needed:
        action_needed = _action_needed(row.get("passed", "").lower() == "true", on_brief, name_quality, lane_discovery, names_to_cut)
    if not notes:
        notes = _judge_notes(row, on_brief, name_quality, lane_discovery, names_to_cut)
    row.update(
        {
            "judge_score": str(judge_score),
            "judge_on_brief_1_5": str(on_brief),
            "judge_name_quality_1_5": str(name_quality),
            "judge_lane_discovery_1_5": str(lane_discovery),
            "judge_would_save_any": would_save,
            "judge_names_to_cut": " | ".join(names_to_cut),
            "judge_notes": f"[{judge_kind}] {notes}",
            "action_needed": action_needed,
        }
    )
    return row


def summarize(rows: list[dict[str, str]], output_csv: Path, judge_mode: str) -> dict[str, Any]:
    scores = [_float(row.get("judge_score")) for row in rows if row.get("judge_score")]
    by_action: dict[str, int] = {}
    for row in rows:
        action = row.get("action_needed", "").strip() or "none"
        by_action[action] = by_action.get(action, 0) + 1
    watch_rows = [
        {
            "fixture_id": row.get("fixture_id"),
            "round_number": row.get("round_number"),
            "lane_label": row.get("lane_label"),
            "judge_score": row.get("judge_score"),
            "action_needed": row.get("action_needed"),
            "names_to_cut": row.get("judge_names_to_cut"),
            "top_names": row.get("top_names"),
        }
        for row in rows
        if row.get("action_needed") and row.get("action_needed") != "no action"
    ]
    return {
        "created_at_local_hint": datetime.now().isoformat(timespec="seconds"),
        "judge_mode": judge_mode,
        "output_csv": str(output_csv),
        "row_count": len(rows),
        "average_judge_score": round(mean(scores), 2) if scores else 0,
        "min_judge_score": min(scores) if scores else 0,
        "action_counts": by_action,
        "watch_rows": watch_rows,
    }


def _split_pipe(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def _safe_json(value: str) -> Any:
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return {"raw": value}


def _int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def _float(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def _clamp_1_5(value: int) -> int:
    return max(1, min(5, value))


def _has_obvious_noise(names: list[str]) -> bool:
    return any(len(name.strip()) <= 1 or any(char.isdigit() for char in name) for name in names)


def _names_to_cut(row: dict[str, str], names: list[str]) -> list[str]:
    vertical = row.get("vertical", "")
    cuts: list[str] = []
    for name in names:
        compact = "".join(char for char in name if char.isalnum())
        if vertical == "business" and len(compact) > 16:
            cuts.append(name)
        elif vertical in {"baby", "pet"} and len(compact) > 12:
            cuts.append(name)
    return cuts


def _action_needed(passed: bool, on_brief: int, name_quality: int, lane_discovery: int, cuts: list[str]) -> str:
    if not passed:
        return "engine gate failure"
    if on_brief < 4:
        return "brief-fit review"
    if name_quality < 4 or cuts:
        return "candidate quality review"
    if lane_discovery < 4:
        return "lane discovery review"
    return "no action"


def _judge_notes(row: dict[str, str], on_brief: int, quality: int, lane: int, cuts: list[str]) -> str:
    notes = [
        f"Lane '{row.get('lane_label', '').strip() or 'unspecified'}' scored on-brief={on_brief}, quality={quality}, lane={lane}."
    ]
    if cuts:
        notes.append(f"Review/cut: {', '.join(cuts)}.")
    elif on_brief >= 4 and quality >= 4 and lane >= 4:
        notes.append("Round looks review-ready; no obvious deterministic issue.")
    return " ".join(notes)


def main() -> int:
    if load_dotenv is not None:
        load_dotenv()
    args = parse_args()
    source = latest_audit_csv() if args.latest or not args.csv_path else Path(args.csv_path)
    fieldnames, rows = read_rows(source)
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]
    judged_rows, judge_mode = judge_rows(
        rows,
        use_ai=args.use_ai,
        require_ai=args.require_ai,
        model=args.model,
    )
    if args.out:
        output_csv = Path(args.out)
    else:
        suffix = "-ai-judged.csv" if judge_mode == "ai" else "-judged.csv"
        output_csv = source.with_name(source.stem + suffix)
    write_rows(output_csv, fieldnames, judged_rows)
    summary = summarize(judged_rows, output_csv, judge_mode)
    summary_path = output_csv.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
