"""Baby adapter for the shared Engine Quality framework."""

from __future__ import annotations

import re
from typing import Any

from namengine.core.quality_framework import (
    QualityAdapter,
    explanation_quality_score,
    register_quality_adapter,
)
from namengine.core.prompt_versions import BABY_PROMPT_VERSION
from namengine.core.schemas import NameResult, NamingBrief


BABY_QUALITY_SCORE_VERSION = "baby-quality-score-v1"
# The overall score favors brief fit and real-world usability while keeping
# culture, distinctiveness, sound, and explanation quality independently visible.
BABY_QUALITY_SCORE_WEIGHTS = {
    "fit": 0.30,
    "usability": 0.20,
    "distinctiveness": 0.15,
    "cultural_alignment": 0.15,
    "sound": 0.10,
    "explanation_quality": 0.10,
}

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "in", "is", "it", "more", "name", "not", "of", "on", "or", "the", "to",
    "very", "with", "your",
}
_TRAIT_ALIASES = {
    "soft": {"gentle", "lyrical", "warm", "rounded"},
    "strong": {"bold", "sturdy", "substantial", "tailored"},
    "playful": {"bright", "bouncy", "lively", "energetic"},
    "classic": {"timeless", "traditional", "established"},
    "modern": {"current", "fresh", "contemporary"},
    "distinctive": {"rare", "uncommon", "unexpected", "memorable"},
    "familiar": {"recognizable", "classic", "readable", "easy"},
    "calm": {"gentle", "quiet", "grounded"},
    "elegant": {"refined", "graceful", "polished", "lyrical"},
    "warm": {"gentle", "friendly", "approachable"},
}


def build_baby_taste_thesis(brief: NamingBrief, weighting: dict[str, Any]) -> str:
    """Summarize every Baby taste control in an audit-friendly thesis."""
    inputs = brief.inputs
    context = _joined_values(
        inputs.get("cultural_heritage"),
        inputs.get("cultural_context"),
        inputs.get("family_context"),
        skip={"no preference", "none"},
    ) or "no cultural or family direction supplied"
    feelings = "balanced with no explicit slider weighting"
    if weighting.get("has_slider_weights"):
        weights = weighting.get("weights_0_to_100", {})
        feelings = ", ".join(f"{key} {value}/100" for key, value in weights.items())
        strongest = weighting.get("strongest_signal")
        if strongest:
            feelings += f"; strongest: {strongest}"

    avoidances = _joined_values(
        ", ".join(brief.avoid),
        brief.notes,
    ) or "none supplied"
    return " ".join(
        [
            f"Style: {_input(inputs, 'style')}",
            f"Familiarity: {_input(inputs, 'familiarity_preference')}",
            f"Distinctiveness: {_input(inputs, 'timeless_vs_distinctive')}",
            f"Sound: {_input(inputs, 'sound')}",
            f"Cultural/family context: {context}",
            f"Discovery: {_input(inputs, 'discovery_style')}",
            f"Feelings Scale: {feelings}",
            f"Avoidances/notes: {avoidances}",
        ]
    )


def improve_baby_explanations(results: list[NameResult], brief: NamingBrief) -> None:
    """Write concise, brief-specific rationales with varied openings and honest tradeoffs."""
    inputs = brief.inputs
    style = _direction(inputs, "style", "overall").lower()
    sound = _direction(inputs, "sound", "wearable").lower()
    familiarity = _direction(inputs, "familiarity_preference", "balanced").lower()
    distinctiveness = _direction(inputs, "timeless_vs_distinctive", "balanced").lower()
    discovery = _direction(inputs, "discovery_style", "balanced discovery").lower()
    heritage = _joined_values(
        inputs.get("cultural_heritage"),
        inputs.get("cultural_context"),
        skip={"no preference", "none"},
    )
    has_family_context = bool(str(inputs.get("family_context") or "").strip())

    for index, result in enumerate(results):
        openings = (
            (
                f"{result.name} fits the {style} brief through its {sound} sound and "
                f"{familiarity} familiarity."
            ),
            (
                f"For this {style} direction, {result.name} brings a {sound} feel while "
                f"staying {familiarity}."
            ),
            (
                f"{result.name} earns a place by balancing {style} style, {sound} sound, "
                f"and a {familiarity} level of recognition."
            ),
            f"What makes {result.name} useful here is its {sound} feel within the {style} direction.",
            f"{result.name} stands out as a {style} option that still feels {familiarity}.",
            f"Parents seeking a {sound}, {style} choice may value {result.name}'s everyday shape.",
            f"In this list, {result.name} covers the {style} and {familiarity} part of the brief.",
            f"At this stage, {result.name} offers a {sound} route to the requested {style} style.",
        )
        opening = openings[index % len(openings)]

        details = [opening, f"It supports the {distinctiveness} and {discovery} goals."]
        if heritage:
            origin = result.origin or "stated origin"
            details.append(f"For {heritage}, verify its {origin} context with the family.")
        elif has_family_context:
            details.append("It is still worth saying with the surname and sibling set you shared.")
        if brief.avoid:
            details.append("It avoids the names explicitly ruled out in the brief.")

        risk = next((item.strip().rstrip(".") for item in result.risks if item.strip()), "")
        if risk:
            if risk.lower().startswith("low practical risk"):
                if _number(result.scores.get("distinctiveness"), 0.58) >= 0.7:
                    risk = "its less familiar profile may need an extra pronunciation or repetition"
                else:
                    risk = "its familiarity may feel less surprising in some communities"
            details.append(f"Tradeoff: {risk}.")
        result.why_this_name = _limit_words(" ".join(details), 68)
        result.fit_note = _limit_words(
            f"{result.name} is strongest if you want {style}, {sound} energy with {familiarity} familiarity; test surname flow and family associations.",
            30,
        )


def score_baby_dimensions(
    result: NameResult,
    brief: NamingBrief,
) -> tuple[dict[str, float], list[str]]:
    """Return Baby-specific dimensions; the framework computes the overall score."""
    facts = " ".join(
        [result.name, result.tagline, result.origin, result.meaning, " ".join(result.tags)]
    ).lower()
    explanation = f"{result.why_this_name} {result.fit_note}".lower()
    inputs = brief.inputs
    style_score = _text_alignment(str(inputs.get("style") or ""), f"{facts} {explanation}")
    familiarity_score = _preference_alignment(result, brief, "familiarity_preference")
    distinctiveness_score = _preference_alignment(result, brief, "timeless_vs_distinctive")
    sound_score = _sound_alignment(result, str(inputs.get("sound") or ""), facts, explanation)
    cultural_score = _cultural_alignment(result, brief, facts, explanation)
    fit_score = _rounded(
        (style_score + familiarity_score + distinctiveness_score + sound_score + cultural_score) / 5
    )
    usability_score = _usability_score(result)
    explanation_score = explanation_quality_score(result, brief)

    scores = {
        "fit": fit_score,
        "usability": usability_score,
        "distinctiveness": distinctiveness_score,
        "cultural_alignment": cultural_score,
        "sound": sound_score,
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


def evaluate_baby_result_list(brief: NamingBrief, results: list[NameResult]) -> dict[str, float]:
    """Evaluate a list by quality attributes rather than expected name equality."""
    if not results:
        return {key: 0.0 for key in _evaluation_attribute_names()}

    dimensions: list[dict[str, float]] = []
    for result in results:
        scores, _reasons = score_baby_dimensions(result, brief)
        dimensions.append(scores)

    def average(key: str) -> float:
        return _rounded(sum(row[key] for row in dimensions) / len(dimensions))

    style_alignment = _rounded(
        sum(
            _text_alignment(
                str(brief.inputs.get("style") or ""),
                " ".join(
                    [
                        result.tagline,
                        result.origin,
                        result.meaning,
                        result.why_this_name,
                        result.fit_note,
                        " ".join(result.tags),
                    ]
                ),
            )
            for result in results
        )
        / len(results)
    )

    clean_names = [result.name.strip().lower() for result in results if result.name.strip()]
    unique_ratio = len(set(clean_names)) / len(results)
    initials = {name[0] for name in clean_names if name}
    initial_ratio = min(1.0, len(initials) / max(3, min(len(results), 6)))
    violations = _obvious_brief_violations(brief, results)
    return {
        "style_alignment": style_alignment,
        "familiarity_alignment": _rounded(
            sum(_preference_alignment(result, brief, "familiarity_preference") for result in results)
            / len(results)
        ),
        "distinctiveness_alignment": average("distinctiveness"),
        "sound_alignment": average("sound"),
        "cultural_context_alignment": average("cultural_alignment"),
        "explanation_specificity": average("explanation_quality"),
        "list_diversity": _rounded(unique_ratio * 0.6 + initial_ratio * 0.4),
        "absence_of_obvious_brief_violations": _rounded(1.0 - violations / len(results)),
    }


def _evaluation_attribute_names() -> tuple[str, ...]:
    return (
        "style_alignment",
        "familiarity_alignment",
        "distinctiveness_alignment",
        "sound_alignment",
        "cultural_context_alignment",
        "explanation_specificity",
        "list_diversity",
        "absence_of_obvious_brief_violations",
    )


def _text_alignment(requested: str, candidate_text: str) -> float:
    requested_tokens = _expanded_tokens(requested)
    if not requested_tokens:
        return 0.8
    candidate_tokens = _expanded_tokens(candidate_text)
    overlap = len(requested_tokens & candidate_tokens)
    return _rounded(min(1.0, 0.45 + 0.55 * overlap / min(3, len(requested_tokens))))


def _preference_alignment(result: NameResult, brief: NamingBrief, field: str) -> float:
    requested = str(brief.inputs.get(field) or "").lower()
    if not requested:
        return 0.8
    target = 0.55
    if any(word in requested for word in ("timeless", "familiar", "recognizable", "easy")):
        target = 0.35
    if any(word in requested for word in ("distinctive", "rarer", "less common", "unexpected")):
        target = 0.82
    candidate = _number(result.scores.get("distinctiveness"), 0.58)
    return _rounded(max(0.0, 1.0 - abs(candidate - target)))


def _sound_alignment(result: NameResult, requested: str, facts: str, explanation: str) -> float:
    model_score = _number(result.scores.get("sound"), _number(result.scores.get("callability"), 0.6))
    lexical = _text_alignment(requested, f"{facts} {explanation}")
    return _rounded(lexical * 0.65 + model_score * 0.35)


def _cultural_alignment(
    result: NameResult,
    brief: NamingBrief,
    facts: str,
    explanation: str,
) -> float:
    requested = _joined_values(
        brief.inputs.get("cultural_heritage"),
        brief.inputs.get("cultural_context"),
        skip={"no preference", "none"},
    )
    if not requested or requested.lower() in {"family heritage", "no preference"}:
        if str(brief.inputs.get("family_context") or "").strip():
            family_terms = {"family", "surname", "sibling"}
            return 0.85 if family_terms & _expanded_tokens(explanation) else 0.55
        return 0.85
    model_score = _number(result.scores.get("cultural_alignment"), 0.5)
    lexical = _text_alignment(requested, facts)
    return _rounded(lexical * 0.75 + model_score * 0.25)


def _usability_score(result: NameResult) -> float:
    model_score = _number(result.scores.get("usability"), _number(result.scores.get("callability"), 0.6))
    length_score = 0.95 if 3 <= len(result.name) <= 9 else 0.72
    pronunciation_score = 0.9 if result.pronunciation else 0.55
    risk_text = " ".join(result.risks).lower()
    friction = 0.18 if any(term in risk_text for term in ("hard to pronounce", "teasing", "confusing")) else 0.0
    return _rounded(max(0.0, model_score * 0.5 + length_score * 0.3 + pronunciation_score * 0.2 - friction))


def _obvious_brief_violations(brief: NamingBrief, results: list[NameResult]) -> int:
    avoid = {_clean(item) for item in brief.avoid}
    violations = 0
    seen: set[str] = set()
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


def _joined_values(*values: Any, skip: set[str] | None = None) -> str:
    skipped = {item.lower() for item in (skip or set())}
    clean = []
    for value in values:
        text = str(value or "").strip()
        if text and text.lower() not in skipped and text not in clean:
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


BABY_QUALITY_ADAPTER = QualityAdapter(
    vertical_slug="baby",
    prompt_version=BABY_PROMPT_VERSION,
    score_version=BABY_QUALITY_SCORE_VERSION,
    score_weights=BABY_QUALITY_SCORE_WEIGHTS,
    model_score_keys=tuple(BABY_QUALITY_SCORE_WEIGHTS),
    prompt_guidance=(
        "Explain why each name fits this specific parent brief, not only its meaning.",
        "Mention a relevant tradeoff honestly and keep the explanation concise.",
        "Use varied, parent-friendly phrasing across the list.",
        "Treat model scores as evidence; the application makes the final rank.",
    ),
    build_taste_thesis=build_baby_taste_thesis,
    score_dimensions=score_baby_dimensions,
    improve_explanations=improve_baby_explanations,
    evaluate_attributes=evaluate_baby_result_list,
)
register_quality_adapter(BABY_QUALITY_ADAPTER)
