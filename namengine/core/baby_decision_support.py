"""Decision-support composition for Baby name details.

The generator owns rich recommendation reasoning. This module keeps older
stored sessions useful without inventing facts or treating model scores as
calibrated measurements.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from typing import Any


_PREFERENCE_LABELS = {
    "style": "Style direction",
    "sound": "Sound",
    "discovery_style": "Discovery style",
    "timeless_vs_distinctive": "Familiarity balance",
    "familiarity_preference": "Familiarity",
    "cultural_heritage": "Cultural or heritage direction",
    "cultural_context": "Inspiration",
}
_COMPARISON_LABELS = {
    "softer_than": "Softer than {name}.",
    "stronger_than": "Stronger in feel than {name}.",
    "more_familiar_than": "More familiar than {name}.",
    "more_distinctive_than": "More distinctive than {name}.",
}
_TECHNICAL_STYLE_KEYS = {
    "callability",
    "warmth",
    "distinctiveness",
    "baby_gender_direction",
    "baby_pronunciation",
    "baby_initials",
    "baby_popularity",
}


def build_baby_decision_support(
    result: Mapping[str, Any],
    session: Mapping[str, Any],
    taste_profile: Mapping[str, Any] | None,
    available_results: list[Mapping[str, Any]],
    reaction_value: str = "",
) -> dict[str, Any]:
    """Return concise, evidence-bounded content for the Baby detail page."""

    brief = _brief(session)
    inputs = brief.get("inputs") if isinstance(brief.get("inputs"), Mapping) else {}
    profile = taste_profile if isinstance(taste_profile, Mapping) else {}

    matched_preferences = _structured_preferences(result.get("matched_preferences"))
    if not matched_preferences:
        matched_preferences = _derived_preferences(result, inputs)

    recommendation_reason = _text(result.get("recommendation_reason"))
    if not recommendation_reason:
        recommendation_reason = _personalized_legacy_reason(result, inputs, matched_preferences)

    strongest_fit = _text(result.get("strongest_fit"))
    if not strongest_fit:
        strongest_fit = _distinct_fit_note(result, recommendation_reason, inputs)

    tradeoffs = _supported_tradeoffs(result)
    tradeoffs.extend(_reliable_validation_cautions(result.get("validation")))
    tradeoffs = _unique(tradeoffs)[:4]

    return {
        "recommendation_reason": recommendation_reason,
        "matched_preferences": matched_preferences[:4],
        "strongest_fit": strongest_fit,
        "real_life_impression": _string_map(result.get("real_life_impression")),
        "family_fit": _string_map(result.get("family_fit")),
        "nickname_considerations": _nickname_map(result.get("nickname_considerations")),
        "comparisons": _comparisons(result, profile, available_results),
        "tradeoffs": tradeoffs,
        "practical_checks": _practical_checks(result.get("validation")),
        "confidence_note": _text(result.get("confidence_note")),
        "taste_insight": _taste_insight(profile, available_results),
        "current_reaction": reaction_value,
    }


def _brief(session: Mapping[str, Any]) -> dict[str, Any]:
    raw = session.get("brief_json")
    if isinstance(raw, Mapping):
        return dict(raw)
    try:
        parsed = json.loads(str(raw or "{}"))
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _structured_preferences(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, Mapping):
            continue
        preference = _text(row.get("preference"))
        evidence = _text(row.get("evidence"))
        fit = _text(row.get("fit"))
        if preference and evidence and fit:
            items.append({"preference": preference, "evidence": evidence, "fit": fit})
    return items


def _derived_preferences(
    result: Mapping[str, Any], inputs: Mapping[str, Any]
) -> list[dict[str, str]]:
    tags = {item.casefold(): item for item in _strings(result.get("tags"))}
    searchable = " ".join(
        _text(result.get(key)) for key in ("tagline", "why_this_name", "fit_note")
    ).casefold()
    items: list[dict[str, str]] = []
    for key, label in _PREFERENCE_LABELS.items():
        value = _text(inputs.get(key))
        if not value or value.casefold() in {"no preference", "none"}:
            continue
        exact_tag = tags.get(value.casefold())
        if not exact_tag and value.casefold() not in searchable:
            continue
        items.append(
            {
                "preference": f"{label}: {value}",
                "evidence": f"You selected {value}.",
                "fit": (
                    f"{result.get('name', 'This name')} carries that signal in its "
                    f"{exact_tag or value} direction."
                ),
            }
        )
    return items


def _personalized_legacy_reason(
    result: Mapping[str, Any],
    inputs: Mapping[str, Any],
    matched_preferences: list[dict[str, str]],
) -> str:
    reason = _text(result.get("why_this_name"))
    if not reason:
        return ""
    lower = reason.casefold()
    boilerplate = (
        "fits the " in lower and " brief" in lower,
        "supports the " in lower and " goals" in lower,
        "aligning with parental hopes" in lower,
        "warm and dignified vibe" in lower,
    )
    if any(boilerplate):
        reason = ""
    evidence = [
        _text(value)
        for key, value in inputs.items()
        if key not in {"notes", "avoid"} and _text(value)
    ]
    if reason and any(value.casefold() in lower for value in evidence):
        return reason
    selected = [
        match["preference"].split(": ", 1)[-1]
        for match in matched_preferences
        if match.get("preference")
    ]
    if selected:
        return (
            f"You asked NamEngine to prioritize {_natural_list(selected[:3])}. "
            f"{result.get('name', 'This name')} carries those signals in its style and sound description."
        )
    return ""


def _distinct_fit_note(
    result: Mapping[str, Any], recommendation_reason: str, inputs: Mapping[str, Any]
) -> str:
    note = _text(result.get("fit_note"))
    if not note or note.casefold() in recommendation_reason.casefold():
        return ""
    lower = note.casefold()
    if "strongest if you want" in lower or "matches the supplied brief" in lower:
        return ""
    evidence = [_text(value) for value in inputs.values() if _text(value)]
    return note if any(value.casefold() in lower for value in evidence) else ""


def _supported_tradeoffs(result: Mapping[str, Any]) -> list[str]:
    validation = result.get("validation")
    has_popularity_source = False
    if isinstance(validation, list):
        has_popularity_source = any(
            isinstance(row, Mapping)
            and _text(row.get("module")) == "baby_popularity"
            and _text(row.get("source"))
            for row in validation
        )
    tradeoffs = []
    source_items = _strings(result.get("tradeoffs")) or _strings(result.get("risks"))
    for item in source_items:
        lower = item.casefold()
        if not has_popularity_source and any(
            term in lower for term in ("popularity", "popular", "overused", "common in")
        ):
            continue
        tradeoffs.append(item)
    return tradeoffs


def _comparisons(
    result: Mapping[str, Any],
    profile: Mapping[str, Any],
    available_results: list[Mapping[str, Any]],
) -> list[dict[str, str]]:
    current_name = _text(result.get("name"))
    reacted = _unique(
        _strings(profile.get("loved_names")) + _strings(profile.get("maybe_names"))
    )
    reacted = [name for name in reacted if name.casefold() != current_name.casefold()]
    if not reacted:
        return []

    by_name = {
        _text(item.get("name")).casefold(): item
        for item in available_results
        if _text(item.get("name"))
    }
    valid_names = {name.casefold(): name for name in reacted if name.casefold() in by_name}
    if not valid_names:
        return []

    comparisons: list[dict[str, str]] = []
    position = result.get("comparison_position")
    if isinstance(position, Mapping):
        for key, template in _COMPARISON_LABELS.items():
            for target in _strings(position.get(key)):
                canonical = valid_names.get(target.casefold())
                if canonical:
                    comparisons.append(
                        {"name": canonical, "comparison": template.format(name=canonical), "evidence": ""}
                    )

    used = {item["name"].casefold() for item in comparisons}
    current_tags = _strings(result.get("tags"))
    current_lookup = {tag.casefold(): tag for tag in current_tags}
    for reacted_name in reacted:
        if len(comparisons) >= 3 or reacted_name.casefold() in used:
            continue
        other = by_name.get(reacted_name.casefold())
        if not other:
            continue
        other_tags = _strings(other.get("tags"))
        other_lookup = {tag.casefold(): tag for tag in other_tags}
        shared = [current_lookup[key] for key in current_lookup.keys() & other_lookup.keys()]
        current_only = [tag for tag in current_tags if tag.casefold() not in other_lookup][:2]
        other_only = [tag for tag in other_tags if tag.casefold() not in current_lookup][:2]
        if not shared and not (current_only and other_only):
            continue
        if shared and current_only and other_only:
            comparison_text = (
                f"Compared with {reacted_name}, it shares {_natural_list(shared[:2])}, "
                f"but {current_name} adds {_natural_list(current_only)} while "
                f"{reacted_name} leans {_natural_list(other_only)}."
            )
        elif shared:
            comparison_text = f"Like {reacted_name}, it carries {_natural_list(shared[:2])}."
        else:
            comparison_text = (
                f"{current_name} leans {_natural_list(current_only)}, while "
                f"{reacted_name} leans {_natural_list(other_only)}."
            )
        comparisons.append(
            {
                "name": reacted_name,
                "comparison": comparison_text,
                "evidence": "Both recommendations carry these style signals.",
            }
        )
    return comparisons[:3]


def _taste_insight(
    profile: Mapping[str, Any], available_results: list[Mapping[str, Any]]
) -> str:
    names = _unique(
        _strings(profile.get("loved_names")) + _strings(profile.get("maybe_names"))
    )
    if not names:
        return ""
    by_name = {
        _text(item.get("name")).casefold(): item
        for item in available_results
        if _text(item.get("name"))
    }
    counts: Counter[str] = Counter()
    labels: dict[str, str] = {}
    for name in names:
        item = by_name.get(name.casefold())
        if not item:
            continue
        for tag in _strings(item.get("tags")):
            key = tag.casefold()
            counts[key] += 1
            labels[key] = tag
    common = [labels[key] for key, count in counts.most_common(3) if count >= 2]
    subject = _natural_list(names[:3])
    if common:
        return f"Your strongest positive signals are {subject}. Across those names, {_natural_list(common)} recur most clearly."
    return f"Your reactions currently point most positively toward {subject}; NamEngine will keep learning as you react to more names."


def _reliable_validation_cautions(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    cautions = []
    for row in value:
        if not isinstance(row, Mapping):
            continue
        status = _text(row.get("status")).casefold()
        confidence = row.get("confidence")
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.0
        if status not in {"warn", "fail"} or confidence_value < 0.75:
            continue
        if _text(row.get("module")) == "baby_popularity" and not _text(row.get("source")):
            continue
        message = _text(row.get("message"))
        if message:
            cautions.append(message)
    return cautions


def _practical_checks(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    checks = []
    for row in value:
        if not isinstance(row, Mapping):
            continue
        module = _text(row.get("module"))
        if module == "baby_popularity" and not _text(row.get("source")):
            continue
        try:
            confidence = float(row.get("confidence"))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < 0.75 and not _text(row.get("source")):
            continue
        label = _text(row.get("label"))
        message = _text(row.get("message"))
        if label and message:
            checks.append(
                {"label": label, "message": message, "status": _text(row.get("status"))}
            )
    return checks


def _nickname_map(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    result = {
        "likely": _strings(value.get("likely")),
        "optional": _strings(value.get("optional")),
        "note": _text(value.get("note")),
    }
    return result if any(result.values()) else {}


def _string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): text for key, item in value.items() if (text := _text(item))}


def _strings(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_text(item) for item in value if _text(item)]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output


def _natural_list(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"
