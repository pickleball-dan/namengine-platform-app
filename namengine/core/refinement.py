"""Refinement round orchestration for the shared platform."""

from __future__ import annotations

import json

from namengine.core.briefs import build_brief
from namengine.core.generation import generate_names
from namengine.core.schemas import NamingBrief, VerticalConfig
from namengine.core.storage import (
    StorageError,
    get_session_snapshot,
    save_session,
)
from namengine.core.taste import build_taste_profile


def build_reaction_effect_summary(snapshot: dict) -> str:
    result_names = {
        row["id"]: row["name"]
        for row in snapshot.get("results", [])
    }
    buckets = {"love": [], "maybe": [], "no": []}
    for reaction in snapshot.get("reactions", []):
        name = result_names.get(reaction["result_id"])
        if name and reaction["value"] in buckets:
            buckets[reaction["value"]].append(name)

    parts = []
    if buckets["love"]:
        parts.append(f"We leaned toward {', '.join(buckets['love'])}.")
    if buckets["maybe"]:
        parts.append(f"We kept {', '.join(buckets['maybe'])} nearby.")
    if buckets["no"]:
        parts.append(f"We moved away from {', '.join(buckets['no'])}.")
    return " ".join(parts) or "We used the first list as a broad taste signal."


def refine_session(
    parent_session_id: str,
    vertical: VerticalConfig,
    instruction: str = "",
) -> tuple[str, NamingBrief, list]:
    snapshot = get_session_snapshot(parent_session_id)
    if snapshot is None:
        raise StorageError("parent session not found")

    parent = snapshot["session"]
    next_round = min(int(parent["round_number"]) + 1, 4)
    if next_round > 4:
        raise StorageError("maximum refinement rounds reached")

    brief_data = json.loads(parent["brief_json"])
    brief = build_brief(vertical, brief_data.get("inputs", {}))
    taste_profile = build_taste_profile(parent_session_id)
    brief.liked_examples = taste_profile.loved_names if taste_profile else _names_for_reaction(snapshot, "love")
    brief.rejected_examples = taste_profile.rejected_names if taste_profile else _names_for_reaction(snapshot, "no")
    brief.notes = instruction

    taste_summary = taste_profile.summary if taste_profile else build_reaction_effect_summary(snapshot)
    previous_names = _all_result_names(snapshot)
    results = generate_names(
        vertical,
        brief,
        round_number=next_round,
        taste_summary=taste_summary,
        taste_profile=taste_profile,
        previous_names=previous_names,
    )
    session_id = f"{parent_session_id}-r{next_round}"
    save_session(
        session_id,
        vertical.slug,
        brief,
        results,
        round_number=next_round,
        parent_session_id=parent_session_id,
        refinement_prompt=instruction,
    )
    return session_id, brief, results


def _names_for_reaction(snapshot: dict, value: str) -> list[str]:
    result_names = {
        row["id"]: row["name"]
        for row in snapshot.get("results", [])
    }
    return [
        result_names[reaction["result_id"]]
        for reaction in snapshot.get("reactions", [])
        if reaction["value"] == value and reaction["result_id"] in result_names
    ]


def _all_result_names(snapshot: dict) -> list[str]:
    return [
        str(row["name"])
        for row in snapshot.get("results", [])
        if row.get("name")
    ]
