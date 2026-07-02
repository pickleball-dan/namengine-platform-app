"""Build structured taste profiles from stored naming reactions."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from namengine.core.schemas import TasteProfile
from namengine.core.storage import (
    get_session_chain_snapshots,
    save_taste_profile,
)


def build_taste_profile(session_id: str, persist: bool = True) -> TasteProfile | None:
    snapshots = get_session_chain_snapshots(session_id)
    if not snapshots:
        return None

    latest = snapshots[-1]["session"]
    vertical = str(latest["vertical"])
    loved: list[str] = []
    maybe: list[str] = []
    rejected: list[str] = []
    liked_sounds: Counter[str] = Counter()
    disliked_sounds: Counter[str] = Counter()
    style_scores: Counter[str] = Counter()
    style_weights: Counter[str] = Counter()
    rejected_lanes: Counter[str] = Counter()

    for snapshot in snapshots:
        results_by_id = {
            row["id"]: json.loads(row["result_json"])
            for row in snapshot.get("results", [])
        }
        for reaction in snapshot.get("reactions", []):
            result = results_by_id.get(reaction["result_id"])
            if result is None:
                continue

            name = str(result["name"])
            value = str(reaction["value"])
            tags = [str(tag) for tag in result.get("tags", [])]
            scores = result.get("scores", {})

            if value == "love":
                _append_unique(loved, name)
                _count_sound(liked_sounds, name)
                _add_style_signal(style_scores, style_weights, tags, scores, 1.0)
            elif value == "maybe":
                _append_unique(maybe, name)
                _count_sound(liked_sounds, name, weight=0.5)
                _add_style_signal(style_scores, style_weights, tags, scores, 0.5)
            elif value == "no":
                _append_unique(rejected, name)
                _count_sound(disliked_sounds, name)
                for tag in tags:
                    rejected_lanes[tag] += 1

    profile = TasteProfile(
        session_id=session_id,
        vertical=vertical,
        loved_names=loved,
        maybe_names=[name for name in maybe if name not in loved],
        rejected_names=[name for name in rejected if name not in loved],
        liked_sounds=[sound for sound, _ in liked_sounds.most_common(4)],
        disliked_sounds=[sound for sound, _ in disliked_sounds.most_common(4)],
        style_preferences=_normalized_preferences(style_scores, style_weights),
        rejected_lanes=[lane for lane, _ in rejected_lanes.most_common(4)],
        summary=_summarize_profile(loved, maybe, rejected),
    )
    if persist:
        save_taste_profile(profile)
    return profile


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _count_sound(counter: Counter[str], name: str, weight: float = 1.0) -> None:
    clean = "".join(character for character in name.lower() if character.isalpha())
    if clean:
        counter[clean[0]] += weight
    if len(clean) >= 2:
        counter[clean[-1]] += weight


def _add_style_signal(
    scores: Counter[str],
    weights: Counter[str],
    tags: list[str],
    result_scores: dict[str, Any],
    weight: float,
) -> None:
    for tag in tags:
        scores[tag] += weight
        weights[tag] += weight
    for key, value in result_scores.items():
        if isinstance(value, (int, float)):
            scores[str(key)] += float(value) * weight
            weights[str(key)] += weight


def _normalized_preferences(
    scores: Counter[str],
    weights: Counter[str],
) -> dict[str, float]:
    return {
        key: round(scores[key] / weights[key], 2)
        for key, _ in scores.most_common(8)
        if weights[key] > 0
    }


def _summarize_profile(
    loved: list[str],
    maybe: list[str],
    rejected: list[str],
) -> str:
    parts = []
    if loved:
        parts.append(f"Strongest signal: {', '.join(loved[:3])}.")
    elif maybe:
        parts.append(f"Early interest around {', '.join(maybe[:3])}.")
    else:
        parts.append("Taste signal is still broad.")

    if rejected:
        parts.append(f"Avoid drifting toward {', '.join(rejected[:3])}.")
    return " ".join(parts)
