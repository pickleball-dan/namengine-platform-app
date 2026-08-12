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
    liked_territories: Counter[str] = Counter()
    disliked_territories: Counter[str] = Counter()
    liked_rationales: Counter[str] = Counter()
    disliked_rationales: Counter[str] = Counter()
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
            metadata_signal = _metadata_signal_for_result(result)

            if value == "love":
                _append_unique(loved, name)
                _count_sound(liked_sounds, name)
                _add_metadata_signal(liked_territories, liked_rationales, metadata_signal)
                _add_strategy_signal(liked_rationales, style_scores, style_weights, result)
                _add_style_signal(style_scores, style_weights, tags + metadata_signal["tags"], scores, 1.0)
            elif value == "maybe":
                # Legacy compatibility only: current product reactions do not expose Maybe.
                _append_unique(maybe, name)
                _count_sound(liked_sounds, name, weight=0.5)
                _add_metadata_signal(liked_territories, liked_rationales, metadata_signal, weight=0.5)
                _add_strategy_signal(liked_rationales, style_scores, style_weights, result, weight=0.5)
                _add_style_signal(style_scores, style_weights, tags + metadata_signal["tags"], scores, 0.5)
            elif value == "no":
                _append_unique(rejected, name)
                _count_sound(disliked_sounds, name)
                _add_metadata_signal(disliked_territories, disliked_rationales, metadata_signal)
                for tag in tags + metadata_signal["tags"]:
                    rejected_lanes[tag] += 1

    profile = TasteProfile(
        session_id=session_id,
        vertical=vertical,
        loved_names=loved,
        maybe_names=[name for name in maybe if name not in loved],
        rejected_names=[name for name in rejected if name not in loved],
        liked_sounds=[sound for sound, _ in liked_sounds.most_common(4)],
        disliked_sounds=[sound for sound, _ in disliked_sounds.most_common(4)],
        liked_territories=[territory for territory, _ in liked_territories.most_common(4)],
        disliked_territories=[territory for territory, _ in disliked_territories.most_common(4)],
        liked_rationales=[rationale for rationale, _ in liked_rationales.most_common(4)],
        disliked_rationales=[rationale for rationale, _ in disliked_rationales.most_common(4)],
        style_preferences=_normalized_preferences(style_scores, style_weights),
        rejected_lanes=[lane for lane, _ in rejected_lanes.most_common(4)],
        summary=_summarize_profile(loved, maybe, rejected),
    )
    if persist:
        save_taste_profile(profile)
    return profile


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _count_sound(counter: Counter[str], name: str, weight: float = 1.0) -> None:
    clean = "".join(character for character in name.lower() if character.isalpha())
    if clean:
        counter[clean[0]] += weight
    if len(clean) >= 2:
        counter[clean[-1]] += weight


def _metadata_signal_for_result(result: dict[str, Any]) -> dict[str, list[str]]:
    metadata = result.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    candidates = _candidate_metadata_for_name(str(result.get("name", "")), metadata)
    territories: list[str] = []
    rationales: list[str] = []
    tags: list[str] = []

    for candidate in candidates:
        _append_unique(territories, str(candidate.get("territory", "")).strip())
        _append_unique(rationales, str(candidate.get("rationale", "")).strip())
        for tag in _string_list(candidate.get("tags")):
            _append_unique(tags, tag)

    return {
        "territories": territories,
        "rationales": rationales,
        "tags": tags,
    }


def _candidate_metadata_for_name(name: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    key = _name_key(name)
    if not key:
        return []

    matches: list[dict[str, Any]] = []
    for bucket_name in ("candidate_pool", "rejected_candidates"):
        bucket = metadata.get(bucket_name)
        if not isinstance(bucket, list):
            continue
        for item in bucket:
            if isinstance(item, dict) and _name_key(str(item.get("name", ""))) == key:
                matches.append(item)
    return matches


def _add_metadata_signal(
    territories: Counter[str],
    rationales: Counter[str],
    signal: dict[str, list[str]],
    weight: float = 1.0,
) -> None:
    for territory in signal["territories"]:
        territories[territory] += weight
    for rationale in signal["rationales"]:
        rationales[rationale] += weight


def _add_strategy_signal(
    rationales: Counter[str],
    style_scores: Counter[str],
    style_weights: Counter[str],
    result: dict[str, Any],
    weight: float = 1.0,
) -> None:
    metadata = result.get("metadata", {})
    if not isinstance(metadata, dict):
        return
    taste_strategy = metadata.get("taste_strategy")
    if not isinstance(taste_strategy, dict):
        return

    thesis = str(taste_strategy.get("taste_thesis", "")).strip()
    if thesis:
        rationales[thesis] += weight
    for value in taste_strategy.values():
        if isinstance(value, str):
            continue
        for item in _string_list(value):
            style_scores[item] += weight
            style_weights[item] += weight


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _name_key(name: str) -> str:
    return "".join(character for character in name.lower() if character.isalnum())


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
