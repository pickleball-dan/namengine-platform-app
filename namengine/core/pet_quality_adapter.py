"""Pet adapter for the shared Engine Quality framework."""

from __future__ import annotations

import re
from typing import Any

from namengine.core.quality_framework import (
    QualityAdapter,
    explanation_quality_score,
    register_quality_adapter,
)
from namengine.core.prompt_versions import PET_PROMPT_VERSION
from namengine.core.schemas import NameResult, NamingBrief


PET_QUALITY_SCORE_VERSION = "pet-quality-score-v1"
PET_QUALITY_SCORE_WEIGHTS = {
    "fit": 0.25,
    "callability": 0.25,
    "personality_match": 0.18,
    "distinctiveness": 0.12,
    "warmth": 0.10,
    "explanation_quality": 0.10,
}

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "in", "is", "it", "name", "not", "of", "on", "or", "pet", "the", "to",
    "very", "with", "your",
}
_TRAIT_ALIASES = {
    "playful": {"bright", "bouncy", "lively", "goofy", "funny", "quirky"},
    "loyal": {"devoted", "steady", "trusty", "faithful"},
    "gentle": {"soft", "kind", "warm", "calm", "sweet"},
    "elegant": {"refined", "graceful", "polished", "regal"},
    "brave": {"bold", "strong", "sturdy", "tough"},
    "curious": {"bright", "alert", "clever", "adventurous"},
    "mischievous": {"impish", "quirky", "playful", "spark"},
    "regal": {"noble", "elegant", "stately"},
    "adventurous": {"outdoor", "bold", "roaming", "trail"},
    "quirky": {"offbeat", "funny", "playful", "distinctive"},
    "sweet": {"gentle", "warm", "soft", "friendly"},
    "tough": {"strong", "sturdy", "bold", "brave"},
    "classic": {"timeless", "familiar", "traditional"},
    "modern": {"fresh", "current", "clean"},
    "soft": {"gentle", "warm", "rounded"},
    "strong": {"bold", "tailored", "sturdy"},
    "uncommon": {"distinctive", "rare", "unexpected", "memorable"},
}


def build_pet_taste_thesis(brief: NamingBrief, weighting: dict[str, Any]) -> str:
    """Summarize every Pet taste control in an audit-friendly thesis."""
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
            f"Pet: {_input(inputs, 'pet_type')}",
            f"Gender: {_input(inputs, 'pet_gender')}",
            f"Breed: {_input(inputs, 'pet_breed')}",
            f"Color: {_input(inputs, 'pet_color')}",
            f"Life stage: {_input(inputs, 'pet_life_stage')}",
            f"Style: {_input(inputs, 'style')}",
            f"Discovery: {_input(inputs, 'discovery_style')}",
            f"Distinctiveness: {_input(inputs, 'timeless_vs_distinctive')}",
            f"Familiarity: {_input(inputs, 'familiarity_preference')}",
            f"Callability: {_input(inputs, 'pronunciation_importance')}",
            f"Personality: {_input(inputs, 'vibe')}",
            f"Inspiration: {_input(inputs, 'cultural_context')}",
            f"Notes/tensions: {_input(inputs, 'partner_alignment')}",
            f"Feelings Scale: {feelings}",
            f"Avoidances/notes: {avoidances}",
        ]
    )


def improve_pet_explanations(results: list[NameResult], brief: NamingBrief) -> None:
    """Write concise Pet-specific rationales with callability and personality evidence."""
    inputs = brief.inputs
    pet = _direction(inputs, "pet_type", "pet").lower()
    style = _direction(inputs, "style", "pet-ready").lower()
    personality = _direction(inputs, "vibe", "their personality").lower()
    callability = _direction(inputs, "pronunciation_importance", "everyday callability").lower()
    portrait = _joined_values(inputs.get("pet_breed"), inputs.get("pet_color"))
    life_stage = str(inputs.get("pet_life_stage") or "").strip().lower()

    for index, result in enumerate(results):
        openings = (
            f"{result.name} fits a {personality} {pet} because it keeps the sound callable while staying in the {style} lane.",
            f"For this {pet}, {result.name} balances {style} style with a name shape that is easy to use out loud.",
            f"{result.name} earns a spot by connecting the pet's {personality} side to practical everyday calling.",
            f"What helps {result.name} work here is the mix of {callability} and {style} warmth.",
        )
        details = [openings[index % len(openings)]]
        if portrait:
            details.append(f"It can sit naturally with the portrait details you gave: {portrait}.")
        if life_stage:
            details.append(f"It is usable for a {life_stage} pet, not just a one-stage nickname.")
        if brief.avoid:
            details.append("It avoids the names explicitly ruled out in the brief.")

        risk = next((item.strip().rstrip(".") for item in result.risks if item.strip()), "")
        if risk:
            details.append(f"Tradeoff: {risk}.")
        result.why_this_name = _limit_words(" ".join(details), 62)
        result.fit_note = _limit_words(
            f"Best if you want a {style}, {personality} name that still feels natural to call across the room.",
            28,
        )


def score_pet_dimensions(result: NameResult, brief: NamingBrief) -> tuple[dict[str, float], list[str]]:
    """Return Pet-specific quality dimensions; the framework computes the weighted score."""
    facts = " ".join(
        [result.name, result.tagline, result.origin, result.meaning, " ".join(result.tags)]
    ).lower()
    explanation = f"{result.why_this_name} {result.fit_note}".lower()
    inputs = brief.inputs

    style_score = _text_alignment(str(inputs.get("style") or ""), f"{facts} {explanation}")
    personality_score = _text_alignment(str(inputs.get("vibe") or ""), f"{facts} {explanation}")
    inspiration_score = _text_alignment(str(inputs.get("cultural_context") or ""), f"{facts} {explanation}")
    fit_score = _rounded(style_score * 0.45 + personality_score * 0.4 + inspiration_score * 0.15)
    callability_score = _callability_score(result)
    distinctiveness_score = _preference_alignment(result, brief)
    warmth_score = _number(result.scores.get("warmth"), _text_alignment("warm gentle friendly", f"{facts} {explanation}"))
    explanation_score = explanation_quality_score(result, brief)

    scores = {
        "fit": fit_score,
        "callability": callability_score,
        "personality_match": personality_score,
        "distinctiveness": distinctiveness_score,
        "warmth": warmth_score,
        "explanation_quality": explanation_score,
    }
    reasons = [
        f"{key.replace('_', ' ')} {value:.2f}"
        for key, value in scores.items()
        if key != "overall" and value >= 0.75
    ]
    if result.risks:
        reasons.append("tradeoff documented")
    return scores, reasons


def evaluate_pet_result_list(brief: NamingBrief, results: list[NameResult]) -> dict[str, float]:
    """Evaluate a Pet list by quality attributes rather than exact expected names."""
    if not results:
        return {
            "callability_alignment": 0.0,
            "personality_alignment": 0.0,
            "style_alignment": 0.0,
            "list_diversity": 0.0,
            "absence_of_obvious_brief_violations": 0.0,
        }
    dimensions = [score_pet_dimensions(result, brief)[0] for result in results]
    clean_names = [result.name.strip().lower() for result in results if result.name.strip()]
    unique_ratio = len(set(clean_names)) / len(results)
    initials = {name[0] for name in clean_names if name}
    initial_ratio = min(1.0, len(initials) / max(3, min(len(results), 6)))
    violations = _obvious_brief_violations(brief, results)
    return {
        "callability_alignment": _average(dimensions, "callability"),
        "personality_alignment": _average(dimensions, "personality_match"),
        "style_alignment": _average(dimensions, "fit"),
        "list_diversity": _rounded(unique_ratio * 0.6 + initial_ratio * 0.4),
        "absence_of_obvious_brief_violations": _rounded(1.0 - violations / len(results)),
    }


def _text_alignment(requested: str, candidate_text: str) -> float:
    requested_tokens = _expanded_tokens(requested)
    if not requested_tokens:
        return 0.8
    candidate_tokens = _expanded_tokens(candidate_text)
    overlap = len(requested_tokens & candidate_tokens)
    return _rounded(min(1.0, 0.45 + 0.55 * overlap / min(3, len(requested_tokens))))


def _preference_alignment(result: NameResult, brief: NamingBrief) -> float:
    requested = " ".join(
        str(brief.inputs.get(key) or "").lower()
        for key in ("timeless_vs_distinctive", "familiarity_preference")
    )
    target = 0.62
    if any(word in requested for word in ("timeless", "familiar", "recognizable", "easy")):
        target = 0.4
    if any(word in requested for word in ("distinctive", "rarer", "uncommon", "unexpected")):
        target = 0.82
    candidate = _number(result.scores.get("distinctiveness"), 0.62)
    return _rounded(max(0.0, 1.0 - abs(candidate - target)))


def _callability_score(result: NameResult) -> float:
    model_score = _number(result.scores.get("callability"), _number(result.scores.get("pet_callability"), 0.65))
    clean = re.sub(r"[^a-z]", "", result.name.lower())
    length_score = 0.95 if 3 <= len(clean) <= 7 else 0.74
    pronunciation_score = 0.9 if result.pronunciation else 0.58
    return _rounded(model_score * 0.55 + length_score * 0.25 + pronunciation_score * 0.2)


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


PET_QUALITY_ADAPTER = QualityAdapter(
    vertical_slug="pet",
    prompt_version=PET_PROMPT_VERSION,
    score_version=PET_QUALITY_SCORE_VERSION,
    score_weights=PET_QUALITY_SCORE_WEIGHTS,
    model_score_keys=("callability", "warmth", "distinctiveness"),
    prompt_guidance=(
        "Keep every Pet-specific intake field as evidence; do not genericize into Baby naming language.",
        "Prioritize callability, animal personality, and household fit over abstract name beauty.",
        "Tie the rationale to the pet type, personality, style, and practical out-loud use.",
        "Mention one practical tradeoff honestly when relevant.",
    ),
    build_taste_thesis=build_pet_taste_thesis,
    score_dimensions=score_pet_dimensions,
    improve_explanations=improve_pet_explanations,
    evaluate_attributes=evaluate_pet_result_list,
)
register_quality_adapter(PET_QUALITY_ADAPTER)
