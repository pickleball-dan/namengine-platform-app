"""Boat adapter for the shared Engine Quality framework."""

from __future__ import annotations

import re
from typing import Any

from namengine.core.quality_framework import (
    QualityAdapter,
    explanation_quality_score,
    register_quality_adapter,
)
from namengine.core.schemas import NameResult, NamingBrief


BOAT_PROMPT_VERSION = "namengine-boat-quality-v1"
BOAT_QUALITY_SCORE_VERSION = "boat-quality-score-v1"
BOAT_QUALITY_SCORE_WEIGHTS = {
    "radio_clarity": 0.24,
    "vessel_fit": 0.22,
    "nautical_character": 0.18,
    "memorability": 0.14,
    "distinctiveness": 0.12,
    "explanation_quality": 0.10,
}

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "boat", "by", "for", "from",
    "in", "is", "it", "name", "not", "of", "on", "or", "the", "to", "with",
    "your",
}
_TRAIT_ALIASES = {
    "adventurous": {"bold", "open", "voyage", "quest", "roam"},
    "classic": {"traditional", "timeless", "heritage", "proper"},
    "coastal": {"harbor", "bay", "salt", "shore", "tide"},
    "elegant": {"graceful", "polished", "refined"},
    "family": {"warm", "welcoming", "crew"},
    "fun": {"playful", "bright", "witty"},
    "mythic": {"legend", "star", "moon", "goddess", "myth"},
    "nautical": {"sail", "sea", "harbor", "anchor", "tide", "wake"},
    "peaceful": {"calm", "quiet", "serene"},
    "powerful": {"bold", "strong", "surge", "wake"},
    "traditional": {"classic", "heritage", "proper", "maritime"},
}
_NAUTICAL_TERMS = {
    "anchor",
    "bay",
    "blue",
    "cape",
    "coast",
    "cove",
    "harbor",
    "knot",
    "mariner",
    "moon",
    "reef",
    "sail",
    "salt",
    "sea",
    "skipper",
    "star",
    "stern",
    "tide",
    "wake",
    "wave",
    "wind",
}


def build_boat_taste_thesis(brief: NamingBrief, weighting: dict[str, Any]) -> str:
    """Summarize Boat context, style, clarity, and maritime fit signals."""
    inputs = brief.inputs
    feelings = "balanced with no explicit slider weighting"
    if weighting.get("has_slider_weights"):
        weights = weighting.get("weights_0_to_100", {})
        feelings = ", ".join(f"{key} {value}/100" for key, value in weights.items())
        strongest = weighting.get("strongest_signal")
        if strongest:
            feelings += f"; strongest: {strongest}"

    avoidances = _joined_values(", ".join(brief.avoid), brief.notes) or "none supplied"
    return " ".join(
        [
            f"Boat type: {_input(inputs, 'boat_type')}",
            f"Boat size: {_input(inputs, 'boat_size')}",
            f"Use: {_input(inputs, 'use')}",
            f"Waters: {_input(inputs, 'waters')}",
            f"Crew: {_input(inputs, 'crew')}",
            f"Name type: {_input(inputs, 'name_type')}",
            f"Vibe: {_input(inputs, 'vibe')}",
            f"Radio clarity: {_input(inputs, 'radio_name')}",
            f"Inspiration: {_input(inputs, 'inspiration')}",
            f"Feelings Scale: {feelings}",
            f"Avoidances/notes: {avoidances}",
        ]
    )


def improve_boat_explanations(results: list[NameResult], brief: NamingBrief) -> None:
    """Write Boat-specific rationales tied to vessel use, transom fit, and radio clarity."""
    inputs = brief.inputs
    vessel = _direction(inputs, "boat_type", "the vessel").lower()
    use = _direction(inputs, "use", "how the boat will be used").lower()
    style = _direction(inputs, "name_type", "boat-ready").lower()
    vibe = _direction(inputs, "vibe", "maritime character").lower()
    waters = _direction(inputs, "waters", "the water").lower()

    for index, result in enumerate(results):
        original_reason = str(result.why_this_name or "").strip()
        openings = (
            f"{result.name} fits this {vessel} because it has enough radio clarity for hailing while still feeling {vibe}.",
            f"{result.name} balances {style} style with a transom-ready shape for {use}.",
            f"What helps {result.name} work is the mix of maritime character, memorability, and everyday dockside sayability.",
            f"{result.name} earns a spot by connecting the boat's use on {waters} with a name that can be spoken cleanly.",
        )
        details = [openings[index % len(openings)]]
        if original_reason:
            details.append(original_reason)
        if brief.avoid:
            details.append("It avoids the names, themes, or bad-luck signals ruled out in the brief.")

        risk = next((item.strip().rstrip(".") for item in result.risks if item.strip()), "")
        rationale = _limit_words(" ".join(details), 72)
        if risk:
            rationale = f"{rationale} Tradeoff: {risk}."
        result.why_this_name = rationale
        result.fit_note = _limit_words(
            f"Best if you want a {style}, {vibe} boat name that reads well on the stern and stays clear when spoken.",
            32,
        )


def score_boat_dimensions(result: NameResult, brief: NamingBrief) -> tuple[dict[str, float], list[str]]:
    """Return Boat-specific dimensions; the framework computes the weighted score."""
    facts = " ".join(
        [result.name, result.tagline, result.origin, result.meaning, " ".join(result.tags)]
    ).lower()
    explanation = f"{result.why_this_name} {result.fit_note}".lower()
    candidate_text = f"{facts} {explanation}"
    inputs = brief.inputs

    vessel_score = _text_alignment(
        _joined_values(inputs.get("boat_type"), inputs.get("boat_size"), inputs.get("use")),
        candidate_text,
    )
    style_score = _text_alignment(
        _joined_values(inputs.get("name_type"), inputs.get("vibe"), inputs.get("inspiration")),
        candidate_text,
    )
    water_score = _text_alignment(
        _joined_values(inputs.get("waters"), inputs.get("crew")),
        candidate_text,
    )
    vessel_fit = _rounded(vessel_score * 0.5 + style_score * 0.35 + water_score * 0.15)
    radio_clarity = _radio_clarity_score(result)
    nautical_character = _nautical_character_score(result, candidate_text)
    memorability = _memorability_score(result)
    distinctiveness = _distinctiveness_score(result, brief)
    explanation_score = explanation_quality_score(result, brief)

    scores = {
        "radio_clarity": radio_clarity,
        "vessel_fit": vessel_fit,
        "nautical_character": nautical_character,
        "memorability": memorability,
        "distinctiveness": distinctiveness,
        "explanation_quality": explanation_score,
    }
    reasons = [
        f"{key.replace('_', ' ')} {value:.2f}"
        for key, value in scores.items()
        if key != "overall" and value >= 0.75
    ]
    if result.risks:
        reasons.append("boat naming tradeoff documented")
    return scores, reasons


def evaluate_boat_result_list(brief: NamingBrief, results: list[NameResult]) -> dict[str, float]:
    """Evaluate a Boat list by shared quality attributes rather than exact names."""
    if not results:
        return {
            "radio_clarity_alignment": 0.0,
            "vessel_fit_alignment": 0.0,
            "nautical_character_alignment": 0.0,
            "list_diversity": 0.0,
            "absence_of_obvious_brief_violations": 0.0,
        }
    dimensions = [score_boat_dimensions(result, brief)[0] for result in results]
    clean_names = [result.name.strip().lower() for result in results if result.name.strip()]
    unique_ratio = len(set(clean_names)) / len(results)
    initials = {name[0] for name in clean_names if name}
    initial_ratio = min(1.0, len(initials) / max(3, min(len(results), 6)))
    violations = _obvious_brief_violations(brief, results)
    return {
        "radio_clarity_alignment": _average(dimensions, "radio_clarity"),
        "vessel_fit_alignment": _average(dimensions, "vessel_fit"),
        "nautical_character_alignment": _average(dimensions, "nautical_character"),
        "list_diversity": _rounded(unique_ratio * 0.6 + initial_ratio * 0.4),
        "absence_of_obvious_brief_violations": _rounded(1.0 - violations / len(results)),
    }


def _text_alignment(requested: str, candidate_text: str) -> float:
    requested_tokens = _expanded_tokens(requested)
    if not requested_tokens:
        return 0.8
    candidate_tokens = _expanded_tokens(candidate_text)
    overlap = len(requested_tokens & candidate_tokens)
    return _rounded(min(1.0, 0.45 + 0.55 * overlap / min(4, len(requested_tokens))))


def _radio_clarity_score(result: NameResult) -> float:
    model_score = _number(result.scores.get("radio_clarity"), _number(result.scores.get("callability"), 0.68))
    clean = _clean(result.name)
    words = [word for word in result.name.replace("-", " ").replace("'", " ").split() if word.strip()]
    length_score = 0.95 if 4 <= len(clean) <= 18 else 0.68
    word_score = 0.92 if 1 <= len(words) <= 3 else 0.62
    pronunciation_score = 0.9 if result.pronunciation else 0.62
    risk_text = " ".join(result.risks).lower()
    friction = 0.18 if any(term in risk_text for term in ("hard to say", "radio", "confusing", "long")) else 0.0
    return _rounded(max(0.0, model_score * 0.45 + length_score * 0.25 + word_score * 0.15 + pronunciation_score * 0.15 - friction))


def _nautical_character_score(result: NameResult, candidate_text: str) -> float:
    model_score = _number(result.scores.get("nautical_character"), 0.66)
    tokens = _expanded_tokens(candidate_text)
    nautical_overlap = bool(tokens & _NAUTICAL_TERMS)
    tag_bonus = 0.1 if any(_clean(tag) in {"nautical", "maritime", "classic", "coastal"} for tag in result.tags) else 0.0
    return _rounded(model_score * 0.65 + (0.22 if nautical_overlap else 0.06) + tag_bonus)


def _memorability_score(result: NameResult) -> float:
    model_score = _number(result.scores.get("memorability"), 0.68)
    clean = _clean(result.name)
    words = [word for word in result.name.replace("-", " ").split() if word.strip()]
    length_score = 0.92 if 4 <= len(clean) <= 16 else 0.7
    shape_score = 0.9 if len(words) <= 3 else 0.68
    return _rounded(model_score * 0.55 + length_score * 0.25 + shape_score * 0.2)


def _distinctiveness_score(result: NameResult, brief: NamingBrief) -> float:
    requested = _joined_values(brief.inputs.get("name_type"), brief.inputs.get("vibe")).lower()
    target = 0.66
    if any(word in requested for word in ("clever", "wordplay", "pun", "distinctive", "invented")):
        target = 0.82
    if any(word in requested for word in ("classic", "traditional", "proper")):
        target = 0.58
    candidate = _number(result.scores.get("distinctiveness"), 0.66)
    return _rounded(max(0.0, 1.0 - abs(candidate - target)))


def _obvious_brief_violations(brief: NamingBrief, results: list[NameResult]) -> int:
    avoid = {_clean(item) for item in brief.avoid}
    seen: set[str] = set()
    violations = 0
    for result in results:
        key = _clean(result.name)
        if not key or key in seen or key in avoid:
            violations += 1
        seen.add(key)
        if any(getattr(item.status, "value", item.status) == "fail" for item in result.validation):
            violations += 1
    return min(len(results), violations)


def _expanded_tokens(value: str) -> set[str]:
    tokens = {token for token in _WORD_RE.findall(value.lower()) if token not in _STOP_WORDS}
    expanded = set(tokens)
    for token in tokens:
        expanded.update(_TRAIT_ALIASES.get(token, set()))
    return expanded


def _input(inputs: dict[str, Any], key: str) -> str:
    return str(inputs.get(key) or "not specified").strip()


def _direction(inputs: dict[str, Any], key: str, default: str) -> str:
    return str(inputs.get(key) or default).strip()


def _joined_values(*values: Any) -> str:
    clean = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in clean:
            clean.append(text)
    return "; ".join(clean)


def _limit_words(value: str, limit: int) -> str:
    words = value.split()
    return value if len(words) <= limit else " ".join(words[:limit]).rstrip(".,;") + "."


def _number(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _clean(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _rounded(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


def _average(rows: list[dict[str, float]], key: str) -> float:
    return _rounded(sum(row[key] for row in rows) / len(rows)) if rows else 0.0


BOAT_QUALITY_ADAPTER = QualityAdapter(
    vertical_slug="boat",
    prompt_version=BOAT_PROMPT_VERSION,
    score_version=BOAT_QUALITY_SCORE_VERSION,
    score_weights=BOAT_QUALITY_SCORE_WEIGHTS,
    model_score_keys=("radio_clarity", "vessel_fit", "nautical_character"),
    prompt_guidance=(
        "Keep every Boat-specific intake field as evidence; do not genericize into Baby, Pet, or Business naming language.",
        "Prioritize radio clarity, vessel fit, nautical character, and transom-ready memorability.",
        "Tie rationale to boat type, use, waters, name style, and practical spoken use.",
        "Mention one practical tradeoff honestly when relevant, especially radio or readability friction.",
    ),
    build_taste_thesis=build_boat_taste_thesis,
    score_dimensions=score_boat_dimensions,
    improve_explanations=improve_boat_explanations,
    evaluate_attributes=evaluate_boat_result_list,
)
register_quality_adapter(BOAT_QUALITY_ADAPTER)
