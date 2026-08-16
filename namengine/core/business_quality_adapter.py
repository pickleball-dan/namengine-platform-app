"""Business adapter for the shared Engine Quality framework."""

from __future__ import annotations

import re
from typing import Any

from namengine.core.quality_framework import (
    QualityAdapter,
    explanation_quality_score,
    register_quality_adapter,
)
from namengine.core.prompt_versions import BUSINESS_PROMPT_VERSION
from namengine.core.schemas import NameResult, NamingBrief


BUSINESS_QUALITY_SCORE_VERSION = "business-quality-score-v1"
BUSINESS_QUALITY_SCORE_WEIGHTS = {
    "fit": 0.28,
    "memorability": 0.20,
    "category_fit": 0.18,
    "launch_readiness": 0.16,
    "ownability": 0.10,
    "explanation_quality": 0.08,
}

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "brand", "business", "but", "by",
    "for", "from", "in", "is", "it", "name", "not", "of", "on", "or", "the", "to",
    "very", "with", "your",
}
_TRAIT_ALIASES = {
    "clear": {"clarity", "plain", "direct", "credible"},
    "credible": {"trustworthy", "professional", "grounded", "serious"},
    "modern": {"fresh", "current", "clean", "energetic"},
    "energetic": {"momentum", "active", "bright", "launch"},
    "premium": {"refined", "polished", "elevated"},
    "refined": {"premium", "polished", "elevated"},
    "friendly": {"warm", "approachable", "human"},
    "approachable": {"friendly", "warm", "human"},
    "bold": {"memorable", "strong", "distinctive"},
    "memorable": {"distinctive", "ownable", "bold"},
    "invented": {"ownable", "distinctive", "readable"},
    "classic": {"timeless", "trustworthy", "established"},
    "trustworthy": {"credible", "classic", "reliable"},
    "distinctive": {"ownable", "memorable", "uncommon"},
    "descriptive": {"clear", "category", "plain"},
}


def build_business_taste_thesis(brief: NamingBrief, weighting: dict[str, Any]) -> str:
    """Summarize Business context, taste, and launch-fit signals for auditability."""
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
            f"Business: {_input(inputs, 'business_description')}",
            f"Industry/category: {_input(inputs, 'industry')}",
            f"Stage: {_input(inputs, 'stage')}",
            f"Buyer type: {_input(inputs, 'audience')}",
            f"Market scope: {_input(inputs, 'market_scope')}",
            f"Style signal: {_input(inputs, 'style')}",
            f"Name shape: {_input(inputs, 'name_shape')}",
            f"Distinctiveness: {_input(inputs, 'timeless_vs_distinctive')}",
            f"Inspiration: {_input(inputs, 'cultural_context')}",
            f"Domain/handle priority: {_input(inputs, 'domain_preference')}",
            f"Decision tension: {_input(inputs, 'partner_alignment')}",
            f"Feelings Scale: {feelings}",
            f"Avoidances/notes: {avoidances}",
        ]
    )


def improve_business_explanations(results: list[NameResult], brief: NamingBrief) -> None:
    """Write Business-specific rationales tied to offer, market, audience, and launch risk."""
    inputs = brief.inputs
    offer = _direction(inputs, "business_description", "the core offer")
    industry = _direction(inputs, "industry", "the category")
    audience = _business_market_direction(inputs)
    style = _direction(inputs, "style", "credible and launch-ready").lower()
    domain = _direction(inputs, "domain_preference", "practical domain and handle testing").lower()

    for index, result in enumerate(results):
        original_reason = str(result.why_this_name or "").strip()
        openings = (
            f"{result.name} fits this business because it gives {industry.lower()} a {style} signal without over-explaining the offer.",
            f"For {audience.lower()}, {result.name} balances memorability with enough category flexibility to grow.",
            f"{result.name} earns a spot by making the business feel launch-ready while staying tied to {offer.lower()}.",
            f"What helps {result.name} work is the mix of brandable sound, category fit, and {domain}.",
        )
        details = [openings[index % len(openings)]]
        if original_reason:
            details.append(original_reason)
        if brief.avoid:
            details.append("It avoids the words, competitors, or sounds explicitly ruled out in the brief.")

        risk = next((item.strip().rstrip(".") for item in result.risks if item.strip()), "")
        rationale = _limit_words(" ".join(details), 72)
        if risk:
            rationale = f"{rationale} Tradeoff: {risk}."
        result.why_this_name = rationale
        result.fit_note = _limit_words(
            f"Best if you want a {style} business name for {audience.lower()} that can be checked against category, trademark, domain, and handle realities.",
            32,
        )


def score_business_dimensions(result: NameResult, brief: NamingBrief) -> tuple[dict[str, float], list[str]]:
    """Return Business-specific dimensions; the framework computes the weighted score."""
    facts = " ".join(
        [result.name, result.tagline, result.origin, result.meaning, " ".join(result.tags)]
    ).lower()
    explanation = f"{result.why_this_name} {result.fit_note}".lower()
    inputs = brief.inputs
    style_score = _text_alignment(str(inputs.get("style") or ""), f"{facts} {explanation}")
    audience_score = _text_alignment(
        _joined_values(inputs.get("audience"), inputs.get("market_scope")),
        f"{facts} {explanation}",
    )
    context_score = _text_alignment(
        _joined_values(inputs.get("business_description"), inputs.get("industry")),
        f"{facts} {explanation}",
    )
    fit_score = _rounded(style_score * 0.45 + audience_score * 0.25 + context_score * 0.30)
    memorability_score = _memorability_score(result)
    category_score = _number(result.scores.get("category_fit"), context_score)
    launch_score = _launch_readiness_score(result)
    ownability_score = _ownability_score(result, brief)
    explanation_score = explanation_quality_score(result, brief)

    scores = {
        "fit": fit_score,
        "memorability": memorability_score,
        "category_fit": category_score,
        "launch_readiness": launch_score,
        "ownability": ownability_score,
        "explanation_quality": explanation_score,
    }
    reasons = [
        f"{key.replace('_', ' ')} {value:.2f}"
        for key, value in scores.items()
        if key != "overall" and value >= 0.75
    ]
    if result.risks:
        reasons.append("launch tradeoff documented")
    return scores, reasons


def evaluate_business_result_list(brief: NamingBrief, results: list[NameResult]) -> dict[str, float]:
    """Evaluate a Business list by launch quality attributes rather than exact names."""
    if not results:
        return {
            "business_context_alignment": 0.0,
            "memorability_alignment": 0.0,
            "category_fit_alignment": 0.0,
            "launch_readiness_alignment": 0.0,
            "list_diversity": 0.0,
            "absence_of_obvious_brief_violations": 0.0,
        }
    dimensions = [score_business_dimensions(result, brief)[0] for result in results]
    clean_names = [result.name.strip().lower() for result in results if result.name.strip()]
    unique_ratio = len(set(clean_names)) / len(results)
    initials = {name[0] for name in clean_names if name}
    initial_ratio = min(1.0, len(initials) / max(3, min(len(results), 6)))
    violations = _obvious_brief_violations(brief, results)
    return {
        "business_context_alignment": _average(dimensions, "fit"),
        "memorability_alignment": _average(dimensions, "memorability"),
        "category_fit_alignment": _average(dimensions, "category_fit"),
        "launch_readiness_alignment": _average(dimensions, "launch_readiness"),
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


def _memorability_score(result: NameResult) -> float:
    model_score = _number(result.scores.get("memorability"), 0.68)
    clean = re.sub(r"[^a-z]", "", result.name.lower())
    length_score = 0.92 if 5 <= len(clean) <= 12 else 0.72
    word_count = len([word for word in result.name.replace("&", " ").split() if word.strip()])
    shape_score = 0.9 if word_count <= 2 else 0.72
    return _rounded(model_score * 0.55 + length_score * 0.25 + shape_score * 0.20)


def _launch_readiness_score(result: NameResult) -> float:
    model_score = _number(result.scores.get("launch_readiness"), 0.65)
    validation_scores = [float(item.score) for item in result.validation if item.score is not None]
    validation_score = sum(validation_scores) / len(validation_scores) if validation_scores else 0.72
    risk_text = " ".join(result.risks).lower()
    friction = 0.1 if any(term in risk_text for term in ("trademark", "domain", "competitor")) else 0.0
    return _rounded(max(0.0, model_score * 0.6 + validation_score * 0.4 - friction))


def _ownability_score(result: NameResult, brief: NamingBrief) -> float:
    requested = str(brief.inputs.get("timeless_vs_distinctive") or "").lower()
    clean = re.sub(r"[^a-z]", "", result.name.lower())
    base = 0.68
    if any(word in requested for word in ("distinctive", "ownable", "highly")):
        base = 0.78
    if any(word in requested for word in ("descriptive", "clear")):
        base = 0.62
    if 5 <= len(clean) <= 11:
        base += 0.06
    if any(tag.lower() in {"brandable", "launch-ready", "business"} for tag in result.tags):
        base += 0.06
    return _rounded(base)


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


def _business_market_direction(inputs: dict[str, Any]) -> str:
    buyer_type = str(inputs.get("audience") or "the target audience").strip()
    market_scope = str(inputs.get("market_scope") or "").strip()
    if market_scope and market_scope != "Not sure yet":
        return f"{buyer_type} in a {market_scope.lower()} market"
    return buyer_type


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


def _average(rows: list[dict[str, float]], key: str) -> float:
    return _rounded(sum(row.get(key, 0.0) for row in rows) / len(rows)) if rows else 0.0


def _number(value: Any, default: float) -> float:
    try:
        return _rounded(float(value))
    except (TypeError, ValueError):
        return _rounded(default)


def _rounded(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


def _clean(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


register_quality_adapter(
    QualityAdapter(
        vertical_slug="business",
        prompt_version=BUSINESS_PROMPT_VERSION,
        score_version=BUSINESS_QUALITY_SCORE_VERSION,
        score_weights=BUSINESS_QUALITY_SCORE_WEIGHTS,
        model_score_keys=("memorability", "category_fit", "launch_readiness"),
        prompt_guidance=(
            "Business explanations must tie the name to the offer, audience, category, and launch risk.",
            "Scores must evaluate memorability, category_fit, and launch_readiness instead of baby/pet warmth.",
            "Treat domain, social handle, trademark, and competitor checks as practical risks, not guarantees.",
        ),
        build_taste_thesis=build_business_taste_thesis,
        score_dimensions=score_business_dimensions,
        improve_explanations=improve_business_explanations,
        evaluate_attributes=evaluate_business_result_list,
    )
)
