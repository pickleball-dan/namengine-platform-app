"""Build decision-focused comparison sets from stored reactions."""

from __future__ import annotations

import json
from typing import Any

from namengine.core.storage import get_session_chain_snapshots


def build_compare_items(session_id: str, limit: int = 6) -> list[dict[str, Any]]:
    snapshots = get_session_chain_snapshots(session_id)
    if not snapshots:
        return []

    selected: dict[str, dict[str, Any]] = {}
    for snapshot in snapshots:
        session = snapshot["session"]
        results_by_id = {
            row["id"]: row
            for row in snapshot["results"]
        }
        reactions_by_id = {
            row["result_id"]: row["value"]
            for row in snapshot["reactions"]
        }

        for result_id, value in reactions_by_id.items():
            row = results_by_id.get(result_id)
            if row is None:
                continue

            item = _compare_item_from_row(row, session, value)
            key = item["name"].lower()
            if value == "love":
                selected[key] = item

    items = list(selected.values())

    latest = snapshots[-1]
    for row in latest["results"][:limit]:
        item = _compare_item_from_row(row, latest["session"], "finalist")
        key = item["name"].lower()
        if key not in {existing["name"].lower() for existing in items}:
            items.append(item)
        if len(items) >= limit:
            break

    return items[:limit]


def _compare_item_from_row(row: dict[str, Any], session: dict[str, Any], reaction: str) -> dict[str, Any]:
    result = json.loads(row["result_json"])
    scores = result.get("scores", {})
    risks = result.get("risks", [])
    return {
        "session_id": row["session_id"],
        "result_id": row["id"],
        "round_number": int(session["round_number"]),
        "reaction": reaction,
        "name": result["name"],
        "pronunciation": result.get("pronunciation", ""),
        "tagline": result.get("tagline", ""),
        "best_if": _best_if(result),
        "watch_out": risks[0] if risks else "No obvious concern.",
        "callability": _score_label(scores.get("callability")),
        "warmth": _score_label(scores.get("warmth")),
        "distinctiveness": _score_label(scores.get("distinctiveness")),
        "why_this_name": result.get("why_this_name", ""),
        "fit_note": result.get("fit_note", ""),
    }


def _best_if(result: dict[str, Any]) -> str:
    name = result["name"]
    tags = result.get("tags", [])
    if "callable" in tags:
        return f"Choose {name} if everyday callability matters most."
    return result.get("fit_note") or f"Choose {name} if it feels closest to the personality."


def _score_label(score: float | None) -> str:
    if score is None:
        return "Unknown"
    if score >= 0.86:
        return "High"
    if score >= 0.7:
        return "Medium"
    return "Low"
