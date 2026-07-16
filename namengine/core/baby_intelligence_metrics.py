"""Baby-owned intelligence metrics, candidate diagnostics, and weaknesses."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from namengine.core.baby_quality_adapter import evaluate_baby_result_list
from namengine.core.intelligence_runs import (
    CandidateDiagnostic,
    DiversityAnalysis,
    FixtureIntelligenceResult,
    IntelligenceMetric,
    Weakness,
)
from namengine.core.name_evaluation import NameEvaluationFixture
from namengine.core.quality_framework import explanation_quality_score
from namengine.core.schemas import NameResult, NamingBrief
from namengine.core.validation import is_baby_name_allowed_for_gender


def calculate_baby_intelligence_metrics(
    brief: NamingBrief,
    results: list[NameResult],
    diversity: DiversityAnalysis | None = None,
) -> tuple[IntelligenceMetric, ...]:
    """Baby-owned derived metrics; shared quality scores remain authoritative."""
    if not results:
        return unavailable_baby_metrics("No candidates were generated")
    attributes = evaluate_baby_result_list(brief, results)
    gender = str(brief.inputs.get("gender") or "").casefold()
    gender_value = None if not gender or gender in {"gender-neutral", "surprise me", "no preference"} else round(
        sum(is_baby_name_allowed_for_gender(brief, item.name) for item in results) / len(results), 3
    )
    quality = [quality_dimensions(item) for item in results]
    average = lambda key: round(sum(row.get(key, 0.0) for row in quality) / len(quality), 3)
    context = " ".join(
        str(brief.inputs.get(key) or "")
        for key in ("family_context", "notes", "cultural_context", "cultural_heritage")
    ).casefold()
    risks = [" ".join(item.risks).casefold() for item in results]
    professional_requested = any(word in context for word in ("professional", "adult use", "workplace"))
    professional = None if not professional_requested else round(
        sum(not any(word in risk for word in ("unprofessional", "adult use")) for risk in risks) / len(results), 3
    )
    tease_requested = "teas" in context
    tease = None if not tease_requested else round(sum("teas" not in risk for risk in risks) / len(results), 3)
    honor_requested = any(word in context for word in ("honor", "family name", "named after"))
    honor_value = None if not honor_requested else round(
        sum(any(word in f"{item.why_this_name} {item.fit_note}".casefold() for word in ("honor", "family")) for item in results) / len(results), 3
    )
    cross_requested = any(word in context for word in ("united states", "bilingual", "cross-cultural", "global"))
    cross_value = None if not cross_requested else round(
        ((professional if professional is not None else average("usability")) + average("usability")) / 2, 3
    )
    heritage = str(brief.inputs.get("cultural_heritage") or "").strip().casefold()
    cultural_direction = str(brief.inputs.get("cultural_context") or "").strip().casefold()
    culture_requested = bool(
        (heritage and heritage != "no preference") or cultural_direction
        or any(word in context for word in ("heritage", "culture", "cross-cultural", "global"))
    )
    timeless_requested = bool(str(brief.inputs.get("timeless_vs_distinctive") or "").strip())
    sound_requested = bool(str(brief.inputs.get("sound") or "").strip())
    metadata_complete = round(sum(metadata_completeness(item) for item in results) / len(results), 3)
    diversity_value = diversity.score if diversity and diversity.status == "applicable" else attributes.get("list_diversity")
    values = {
        "gender_fit": gender_value,
        "cultural_relevance": attributes.get("cultural_context_alignment") if culture_requested else None,
        "familiarity": attributes.get("familiarity_alignment"),
        "distinctiveness": attributes.get("distinctiveness_alignment"),
        "timelessness_modernity_fit": attributes.get("distinctiveness_alignment") if timeless_requested else None,
        "sound_fit": attributes.get("sound_alignment") if sound_requested else None,
        "strength_softness_fit": attributes.get("sound_alignment") if sound_requested else None,
        "professional_usability": professional,
        "tease_resistance": tease,
        "honor_name_influence": honor_value,
        "cross_cultural_usability": cross_value,
        "explanation_quality": attributes.get("explanation_specificity"),
        "metadata_completeness": metadata_complete,
        "final_list_coherence": round((attributes.get("style_alignment", 0.0) + (diversity_value or 0.0)) / 2, 3),
    }
    return tuple(metric(code, values[code], "Derived from Baby quality and fixture context") for code in metric_codes())


def analyze_baby_candidate_diversity(results: list[NameResult]) -> DiversityAnalysis:
    """Measure Baby-list variety with thresholds owned by Baby Intelligence."""
    names = [item.name.strip() for item in results if item.name.strip()]
    if len(names) < 2:
        return DiversityAnalysis("not_applicable", None, reasons=("At least two names are required",))
    folded = [name.casefold() for name in names]
    normalized = [normalized_name(name) for name in names]
    exact = duplicates(folded)
    normalized_dupes = normalized_duplicate_variants(folded, normalized)
    near = sorted(
        f"{names[left]}|{names[right]}"
        for left in range(len(names)) for right in range(left + 1, len(names))
        if normalized[left] != normalized[right] and edit_distance(normalized[left], normalized[right]) <= 1
    )
    roots = repeated_parts(normalized, lambda value: value[:3] if len(value) >= 4 else "")
    endings = repeated_parts(normalized, lambda value: value[-2:] if len(value) >= 3 else "")
    sounds = repeated_parts(normalized, lambda value: value[:2])
    first_concentration = largest_share(name[:1] for name in normalized)
    origins = [item.origin.strip().casefold() for item in results if item.origin.strip()]
    cultural = largest_share(origins) if origins else None
    familiarity_bands = [band(quality_dimensions(item).get("distinctiveness", 0.5)) for item in results]
    familiarity = largest_share(familiarity_bands)
    styles = [tag.casefold() for item in results for tag in item.tags if tag.casefold() not in {"wearable", "family-ready"}]
    style = largest_share(styles) if styles else None
    territories = [candidate_territory(item) for item in results]
    known_territories = [item for item in territories if item != "unspecified"]
    territory = largest_share(known_territories) if known_territories else None
    ordering = None if len(known_territories) < 2 else round(
        sum(known_territories[index] != known_territories[index - 1] for index in range(1, len(known_territories)))
        / max(1, len(known_territories) - 1), 3
    )
    penalties = (
        len(exact) * 0.25 + len(normalized_dupes) * 0.20 + len(near) * 0.06
        + max(0.0, first_concentration - 0.5) * 0.35
        + max(0.0, (territory or 0.0) - 0.75) * 0.25
        + max(0.0, familiarity - 0.8) * 0.15
    )
    score = round(max(0.0, min(1.0, 1.0 - penalties)), 3)
    reasons = []
    if exact or normalized_dupes:
        reasons.append("Duplicate candidates reduce meaningful choice")
    if near:
        reasons.append("Near-spelling variants appear in the same list")
    if first_concentration > 0.5:
        reasons.append("More than half of candidates share a first letter")
    if territory is not None and territory > 0.75:
        reasons.append("The list is concentrated in one naming territory")
    if territory is None:
        reasons.append("Naming-territory metadata was not available")
    if not reasons:
        reasons.append("The list is cohesive without material candidate concentration")
    return DiversityAnalysis(
        "applicable", score, tuple(exact), tuple(normalized_dupes), tuple(near[:100]),
        tuple(roots), tuple(endings), tuple(sounds), first_concentration, cultural,
        familiarity, style, territory, ordering, tuple(reasons),
    )


def build_candidate_diagnostics(
    fixture: NameEvaluationFixture, brief: NamingBrief, results: list[NameResult]
) -> tuple[CandidateDiagnostic, ...]:
    references = {item.casefold() for item in fixture.reference_candidates}
    rejections = {item.casefold() for item in fixture.rejection_candidates}
    rows = []
    for rank, result in enumerate(results, 1):
        quality = quality_dimensions(result)
        score = optional_score(result.metadata.get("quality_score"))
        source = str(result.metadata.get("source") or result.metadata.get("provider") or "unknown")[:100]
        reasons = result.metadata.get("quality_reasons", [])
        rows.append(CandidateDiagnostic(
            str(result.id)[:100], result.name[:100], rank, score, quality, score,
            candidate_territory(result), explanation_quality_score(result, brief),
            metadata_completeness(result),
            tuple(str(item)[:200] for item in reasons if isinstance(item, str))[:20],
            (result.name.casefold()[:100], source.casefold(), result.slug.casefold()[:100]),
            result.name.casefold() in references, result.name.casefold() in rejections,
            source if "fallback" in source.casefold() else "",
        ))
    return tuple(rows)


def analyze_baby_weaknesses(
    fixture_results: tuple[FixtureIntelligenceResult, ...],
) -> tuple[Weakness, ...]:
    findings: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"fixtures": set(), "candidates": set(), "impact": 0.0, "count": 0}
    )
    for fixture in fixture_results:
        for criterion in fixture.criterion_results:
            if criterion.get("status") == "fail":
                add_finding(findings, criterion_weakness(str(criterion.get("criterion") or "")), fixture, float(criterion.get("maximum_score") or 0.0))
        for item in fixture.metrics:
            if item.status == "applicable" and item.value is not None and item.value < 0.55:
                add_finding(findings, f"low_{item.code}", fixture, 1.0 - item.value)
        if fixture.diversity.status == "applicable" and (fixture.diversity.score or 0) < 0.7:
            add_finding(findings, "candidate_diversity", fixture, 1.0 - (fixture.diversity.score or 0))
        if fixture.fallback_used:
            add_finding(findings, "fallback_dependence", fixture, 0.4)
        if fixture.execution_error:
            add_finding(findings, "generation_failure", fixture, 1.0)
    rows = []
    for code, data in findings.items():
        subsystem, target = weakness_target(code)
        impact = round(min(1.0, data["impact"] / max(1, data["count"])), 3)
        severity = "critical" if code in {"privacy_safety", "prohibited_name", "generation_failure"} else (
            "major" if impact >= 0.5 else "minor" if impact >= 0.2 else "informational"
        )
        rows.append(Weakness(
            code, tuple(sorted(data["fixtures"])), tuple(sorted(data["candidates"]))[:100],
            severity, data["count"], impact, subsystem,
            f"{code.replace('_', ' ').title()} affected {len(data['fixtures'])} fixture(s)", target,
        ))
    severity_order = {"critical": 0, "major": 1, "minor": 2, "informational": 3}
    return tuple(sorted(rows, key=lambda item: (severity_order[item.severity], -item.weighted_impact, item.code)))


def summarize_baby_metrics(fixtures: list[FixtureIntelligenceResult]) -> tuple[IntelligenceMetric, ...]:
    by_code: dict[str, list[float]] = defaultdict(list)
    for fixture in fixtures:
        for item in fixture.metrics:
            if item.status == "applicable" and item.value is not None:
                by_code[item.code].append(item.value)
    return tuple(metric(
        code, round(sum(by_code[code]) / len(by_code[code]), 3) if by_code[code] else None,
        f"Average across {len(by_code[code])} applicable fixture execution(s)",
    ) for code in metric_codes())


def unavailable_baby_metrics(reason: str) -> tuple[IntelligenceMetric, ...]:
    return tuple(metric(code, None, reason) for code in metric_codes())


def quality_dimensions(result: NameResult) -> dict[str, float]:
    raw = result.metadata.get("quality_scores")
    if not isinstance(raw, dict):
        return {}
    return {
        str(key)[:100]: round(max(0.0, min(1.0, float(value))), 3)
        for key, value in raw.items()
        if key != "overall" and isinstance(value, (int, float))
    }


def metadata_completeness(result: NameResult) -> float:
    required = ("quality_scores", "quality_reasons", "quality_score_version", "source", "prompt_version")
    return round(sum(result.metadata.get(key) not in (None, "", [], {}) for key in required) / len(required), 3)


def candidate_territory(result: NameResult) -> str:
    if result.origin:
        return result.origin[:100].casefold()
    tags = [str(tag) for tag in result.tags if str(tag).casefold() not in {"wearable", "warm", "family-ready"}]
    return tags[0][:100].casefold() if tags else "unspecified"


def metric(code: str, value: float | None, reason: str) -> IntelligenceMetric:
    return IntelligenceMetric(code, "not_applicable" if value is None else "applicable", value, reason[:500])


def metric_codes() -> tuple[str, ...]:
    return (
        "gender_fit", "cultural_relevance", "familiarity", "distinctiveness",
        "timelessness_modernity_fit", "sound_fit", "strength_softness_fit",
        "professional_usability", "tease_resistance", "honor_name_influence",
        "cross_cultural_usability", "explanation_quality", "metadata_completeness",
        "final_list_coherence",
    )


def criterion_weakness(code: str) -> str:
    return {
        "required_candidate_count": "insufficient_candidate_count", "uniqueness": "duplicate_candidates",
        "duplicate_prevention": "duplicate_candidates", "prohibited_names": "prohibited_name",
        "prohibited_patterns": "prohibited_name", "cultural_relevance": "low_cultural_relevance",
        "gender_fit": "low_gender_fit", "style_fit": "low_style_fit",
        "sound_strength_fit": "low_sound_fit", "territory_coverage": "territory_concentration",
        "explanation_completeness": "weak_explanations", "metadata_completeness": "incomplete_metadata",
        "deterministic_ordering": "unstable_ordering", "privacy_safety": "privacy_safety",
    }.get(code, f"criterion_{code}"[:100])


def weakness_target(code: str) -> tuple[str, str]:
    if "intake" in code:
        return "intake normalization", "Review canonical intent mapping and fixture inputs"
    if "cultural" in code or "gender" in code:
        return "candidate generation", "Improve Baby provider evidence and candidate constraints"
    if "diversity" in code or "duplicate" in code or "territory" in code:
        return "post-processing", "Improve Baby list composition and diversity selection"
    if "explanation" in code:
        return "quality adapter", "Improve brief-specific explanation checks"
    if "metadata" in code or "privacy" in code:
        return "post-processing", "Repair safe metadata instrumentation"
    if "fallback" in code:
        return "fallback behavior", "Reduce fallback dependence or improve fallback coverage"
    if "ordering" in code:
        return "ranking", "Review deterministic ranking inputs and tie breaks"
    if "generation" in code:
        return "model/provider", "Improve provider reliability and timeout handling"
    return "evaluation criteria", "Review the failing fixture criterion and its evidence"


def add_finding(findings, code: str, fixture: FixtureIntelligenceResult, impact: float) -> None:
    row = findings[code]
    row["fixtures"].add(fixture.fixture_id)
    row["candidates"].update(item.name for item in fixture.candidates if item.rejection_candidate)
    row["impact"] += max(0.0, min(1.0, impact))
    row["count"] += 1


def normalized_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if value and count > 1)


def normalized_duplicate_variants(folded: list[str], normalized: list[str]) -> list[str]:
    variants: dict[str, set[str]] = defaultdict(set)
    for original, clean in zip(folded, normalized):
        variants[clean].add(original)
    return sorted(clean for clean, originals in variants.items() if clean and len(originals) > 1)


def repeated_parts(values: list[str], getter) -> list[str]:
    return sorted(value for value, count in Counter(getter(item) for item in values).items() if value and count > 1)


def largest_share(values) -> float:
    clean = [value for value in values if value]
    return round(max(Counter(clean).values()) / len(clean), 3) if clean else 0.0


def band(value: float) -> str:
    return "low" if value < 0.4 else "high" if value > 0.7 else "middle"


def edit_distance(left: str, right: str) -> int:
    if abs(len(left) - len(right)) > 1:
        return 2
    previous = list(range(len(right) + 1))
    for index, char in enumerate(left, 1):
        current = [index]
        for other, target in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[other] + 1, previous[other - 1] + (char != target)))
        previous = current
    return previous[-1]


def optional_score(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(max(0.0, min(1.0, float(value))), 3)
