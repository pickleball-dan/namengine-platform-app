"""Build a plain-English diagnostic for changes between naming rounds."""

from __future__ import annotations

import json
from typing import Any


FEELINGS_PREFIX = "taste_strength_"


def build_taste_evolution(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    """Compare two stored session snapshots without changing generation state."""
    parent_brief = _brief(parent)
    child_brief = _brief(child)
    parent_inputs = dict(parent_brief.get("inputs") or {})
    child_inputs = dict(child_brief.get("inputs") or {})
    parent_names = _results(parent)
    child_names = _results(child)
    reactions = _reaction_names(parent, parent_names)
    parent_profile = _profile(parent)
    child_profile = _profile(child)
    updated_profile = child_profile or parent_profile
    previous_strategy = _strategy(parent_names)
    current_strategy = _strategy(child_names)

    intake_rows = _differences(
        _without_feelings(parent_inputs),
        _without_feelings(child_inputs),
    )
    slider_rows = _differences(
        _feelings(parent_inputs),
        _feelings(child_inputs),
        strip_prefix=FEELINGS_PREFIX,
    )
    style_rows = _preference_differences(
        parent_inputs,
        child_inputs,
        parent_profile,
        updated_profile,
        "style",
    )
    sound_rows = _preference_differences(
        parent_inputs,
        child_inputs,
        parent_profile,
        updated_profile,
        "sound",
    )
    strategy_rows = _set_differences(
        "Naming territory",
        _territories(previous_strategy),
        _territories(current_strategy),
    )
    unchanged = [row for row in intake_rows + slider_rows if row["status"] == "unchanged"]
    previous_name_values = [item["name"] for item in parent_names]
    current_name_keys = {item["name"].casefold() for item in child_names}

    return {
        "previous": {
            "round_number": int(parent["session"].get("round_number") or 1),
            "taste_thesis": previous_strategy.get("taste_thesis") or "Not captured for this round.",
            "intake": _without_feelings(parent_inputs),
            "feelings": _feelings(parent_inputs),
            "taste_profile": parent_profile,
            "names": parent_names[:8],
        },
        "user_changes": {
            "reactions": reactions,
            "instruction": str(child["session"].get("refinement_prompt") or "").strip(),
            "intake_changes": intake_rows,
            "slider_changes": slider_rows,
        },
        "learned": {
            "loved_names": _carried_names(reactions["love"], child_brief.get("liked_examples")),
            "rejected_names": _carried_names(reactions["no"], child_brief.get("rejected_examples")),
            "style_changes": style_rows,
            "sound_changes": sound_rows,
            "strategy_changes": strategy_rows,
            "unchanged_preferences": unchanged,
        },
        "new": {
            "round_number": int(child["session"].get("round_number") or 1),
            "taste_thesis": current_strategy.get("taste_thesis") or "Not captured for this round.",
            "taste_profile": updated_profile,
            "taste_profile_source": (
                "Stored on the new round"
                if child_profile
                else "Carried forward from reactions on the previous round"
                if parent_profile
                else "No taste profile was stored"
            ),
            "names": child_names[:8],
            "previous_names_excluded": [
                name for name in previous_name_values if name.casefold() not in current_name_keys
            ],
        },
        "summary": _plain_english_summary(
            parent_names,
            reactions,
            slider_rows,
            intake_rows,
            str(child["session"].get("refinement_prompt") or "").strip(),
        ),
    }


def _brief(snapshot: dict[str, Any]) -> dict[str, Any]:
    return _json_object(snapshot.get("session", {}).get("brief_json"))


def _profile(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    row = snapshot.get("taste_profile")
    if not isinstance(row, dict):
        return None
    profile = _json_object(row.get("profile_json"))
    return profile or None


def _results(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in snapshot.get("results", []):
        payload = _json_object(row.get("result_json"))
        if not payload:
            payload = {"id": row.get("id"), "name": row.get("name")}
        results.append(payload)
    return results


def _strategy(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {}
    metadata = results[0].get("metadata")
    if not isinstance(metadata, dict):
        return {}
    strategy = metadata.get("taste_strategy")
    return strategy if isinstance(strategy, dict) else {}


def _territories(strategy: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for item in strategy.get("naming_territories") or []:
        value = item.get("label") if isinstance(item, dict) else item
        clean = str(value or "").strip()
        if clean and clean not in values:
            values.append(clean)
    return values


def _reaction_names(
    snapshot: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, list[str]]:
    names_by_id = {str(item.get("id")): str(item.get("name")) for item in results}
    buckets = {"love": [], "maybe": [], "no": []}
    for reaction in snapshot.get("reactions", []):
        value = str(reaction.get("value") or "")
        name = names_by_id.get(str(reaction.get("result_id")))
        if value in buckets and name and name not in buckets[value]:
            buckets[value].append(name)
    return buckets


def _without_feelings(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if not str(key).startswith(FEELINGS_PREFIX)}


def _feelings(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if str(key).startswith(FEELINGS_PREFIX)}


def _differences(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    strip_prefix: str = "",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(set(previous) | set(current)):
        before = previous.get(key)
        after = current.get(key)
        label = _label(key[len(strip_prefix) :] if strip_prefix and key.startswith(strip_prefix) else key)
        if key not in previous:
            rows.append(_row(label, None, after, "added"))
        elif key not in current:
            rows.append(_row(label, before, None, "removed"))
        elif before == after:
            rows.append(_row(label, before, after, "unchanged"))
        elif _number(before) is not None and _number(after) is not None:
            status = "increased" if _number(after) > _number(before) else "decreased"
            rows.append(_row(label, before, after, status))
        else:
            rows.append(_row(label, before, None, "removed"))
            rows.append(_row(label, None, after, "added"))
    return rows


def _preference_differences(
    previous_inputs: dict[str, Any],
    current_inputs: dict[str, Any],
    previous_profile: dict[str, Any] | None,
    current_profile: dict[str, Any] | None,
    kind: str,
) -> list[dict[str, Any]]:
    previous = {
        key: value
        for key, value in previous_inputs.items()
        if kind in str(key).lower() and not str(key).startswith(FEELINGS_PREFIX)
    }
    current = {
        key: value
        for key, value in current_inputs.items()
        if kind in str(key).lower() and not str(key).startswith(FEELINGS_PREFIX)
    }
    rows = _differences(previous, current)
    if kind == "style":
        rows.extend(
            _differences(
                (previous_profile or {}).get("style_preferences") or {},
                (current_profile or {}).get("style_preferences") or {},
            )
        )
    else:
        rows.extend(
            _set_differences(
                "Liked sound",
                (previous_profile or {}).get("liked_sounds") or [],
                (current_profile or {}).get("liked_sounds") or [],
            )
        )
        rows.extend(
            _set_differences(
                "Disliked sound",
                (previous_profile or {}).get("disliked_sounds") or [],
                (current_profile or {}).get("disliked_sounds") or [],
            )
        )
    return rows


def _set_differences(label: str, previous: list[Any], current: list[Any]) -> list[dict[str, Any]]:
    before = [str(item) for item in previous]
    after = [str(item) for item in current]
    rows = [_row(label, item, item, "unchanged") for item in before if item in after]
    rows.extend(_row(label, item, None, "removed") for item in before if item not in after)
    rows.extend(_row(label, None, item, "added") for item in after if item not in before)
    return rows


def _carried_names(names: list[str], stored_names: Any) -> list[dict[str, Any]]:
    carried = {str(name).casefold() for name in (stored_names or [])}
    return [{"name": name, "carried": name.casefold() in carried} for name in names]


def _plain_english_summary(
    parent_names: list[dict[str, Any]],
    reactions: dict[str, list[str]],
    slider_rows: list[dict[str, Any]],
    intake_rows: list[dict[str, Any]],
    instruction: str,
) -> str:
    by_name = {str(item.get("name")): item for item in parent_names}
    loved = reactions["love"]
    rejected = reactions["no"]
    increased = [row["label"].lower() for row in slider_rows if row["status"] == "increased"]
    added_preferences = [
        str(row["current"]).lower()
        for row in intake_rows
        if row["status"] == "added" and row.get("current") not in (None, "")
    ]
    all_loved_tags = _tags_for_names(loved, by_name)
    all_rejected_tags = _tags_for_names(rejected, by_name)
    shared_tags = set(all_loved_tags) & set(all_rejected_tags)
    loved_tags = [tag for tag in all_loved_tags if tag not in shared_tags]
    rejected_tags = [tag for tag in all_rejected_tags if tag not in shared_tags]
    parts: list[str] = []

    emphasis = _unique(loved_tags + added_preferences + increased)[:3]
    if loved:
        subject = ", ".join(loved[:2])
        reason = f" because {subject} {'was' if len(loved) == 1 else 'were'} loved"
        if increased:
            slider_noun = "slider was" if len(increased) == 1 else "sliders were"
            reason += f" and the {_join_words(increased[:2])} {slider_noun} raised"
        if emphasis:
            parts.append(f"The engine increased {_join_words(emphasis)} emphasis{reason}.")
        else:
            parts.append(f"The engine leaned toward names like {subject}{reason}.")
    elif increased:
        parts.append(f"The engine increased {_join_words(increased[:2])} emphasis because those sliders were raised.")

    if rejected:
        direction = _join_words(rejected_tags[:2]) or "cues represented by " + ", ".join(rejected[:2])
        parts.append(
            f"It moved away from {direction} because {', '.join(rejected[:2])} "
            f"{'was' if len(rejected) == 1 else 'were'} rejected."
        )
    if instruction:
        ending = "" if instruction.endswith((".", "!", "?")) else "."
        parts.append(f'It also followed the refinement instruction: “{instruction}”{ending}')
    if not parts:
        parts.append("The engine kept the recorded preferences unchanged because no new directional signal was stored.")
    return " ".join(parts)


def _tags_for_names(names: list[str], by_name: dict[str, dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    for name in names:
        for tag in by_name.get(name, {}).get("tags") or []:
            clean = str(tag).strip().lower()
            if clean and clean not in tags:
                tags.append(clean)
    return tags


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _join_words(values: list[str]) -> str:
    if len(values) > 1:
        return ", ".join(values[:-1]) + " and " + values[-1]
    return values[0] if values else ""


def _row(label: str, previous: Any, current: Any, status: str) -> dict[str, Any]:
    return {"label": label, "previous": previous, "current": current, "status": status}


def _label(value: Any) -> str:
    return str(value).replace("_", " ").strip().title()


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}
