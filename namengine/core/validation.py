"""Structured validation pipeline for generated names."""

from __future__ import annotations

from namengine.core.schemas import (
    NamingBrief,
    NameResult,
    ValidationResult,
    ValidationStatus,
    VerticalConfig,
)


VOWELS = set("aeiouy")


def validate_result(
    vertical: VerticalConfig,
    brief: NamingBrief,
    result: NameResult,
) -> list[ValidationResult]:
    if vertical.slug == "pet":
        return _validate_pet_name(brief, result.name)
    return [
        ValidationResult(
            module="validation_not_configured",
            status=ValidationStatus.UNKNOWN,
            label="Validation",
            message="Validation has not been configured for this vertical yet.",
            confidence=0.0,
        )
    ]


def validate_results(
    vertical: VerticalConfig,
    brief: NamingBrief,
    results: list[NameResult],
) -> list[NameResult]:
    for result in results:
        result.validation = validate_result(vertical, brief, result)
        result.scores.update(_scores_from_validation(result.validation))
    return results


def _validate_pet_name(brief: NamingBrief, name: str) -> list[ValidationResult]:
    clean_name = "".join(character for character in name.lower() if character.isalpha())
    avoid = {item.lower() for item in brief.avoid}
    syllable_count = _estimate_syllables(clean_name)
    length = len(clean_name)

    validation = [
        _pet_callability_validation(length, syllable_count),
        _pet_sound_clarity_validation(clean_name),
    ]
    if avoid:
        validation.append(_pet_avoid_validation(clean_name, avoid))
    return validation


def _pet_callability_validation(length: int, syllable_count: int) -> ValidationResult:
    if length <= 6 and syllable_count <= 2:
        return ValidationResult(
            module="pet_callability",
            status=ValidationStatus.PASS,
            label="Callability",
            message="Short sound shape for everyday calling.",
            score=0.94,
            confidence=0.9,
            metadata={"length": length, "syllables": syllable_count},
        )
    return ValidationResult(
        module="pet_callability",
        status=ValidationStatus.WARN,
        label="Callability",
        message="A little longer; test how it feels when called out loud.",
        score=0.72,
        confidence=0.84,
        metadata={"length": length, "syllables": syllable_count},
    )


def _pet_sound_clarity_validation(clean_name: str) -> ValidationResult:
    if clean_name and clean_name[0] in "mnrlstbcfpwh":
        return ValidationResult(
            module="pet_sound_clarity",
            status=ValidationStatus.PASS,
            label="Sound clarity",
            message="Clear opening sound that should be easy to repeat.",
            score=0.9,
            confidence=0.86,
        )
    return ValidationResult(
        module="pet_sound_clarity",
        status=ValidationStatus.WARN,
        label="Sound clarity",
        message="Softer opening sound; say it aloud before committing.",
        score=0.76,
        confidence=0.78,
    )


def _pet_avoid_validation(clean_name: str, avoid: set[str]) -> ValidationResult:
    if clean_name in avoid:
        return ValidationResult(
            module="avoid_match",
            status=ValidationStatus.FAIL,
            label="Avoid list",
            message="This name matches something the user asked to avoid.",
            score=0.0,
            confidence=1.0,
        )
    return ValidationResult(
        module="avoid_match",
        status=ValidationStatus.PASS,
        label="Avoid list",
        message="Does not match the avoid list.",
        score=1.0,
        confidence=1.0,
    )


def _estimate_syllables(clean_name: str) -> int:
    if not clean_name:
        return 0

    groups = 0
    previous_was_vowel = False
    for character in clean_name:
        is_vowel = character in VOWELS
        if is_vowel and not previous_was_vowel:
            groups += 1
        previous_was_vowel = is_vowel
    if clean_name.endswith("e") and groups > 1:
        groups -= 1
    return max(groups, 1)


def _scores_from_validation(validation: list[ValidationResult]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for item in validation:
        if item.score is not None:
            scores[item.module] = item.score
    return scores
