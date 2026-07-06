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

BABY_GIRL_INCOMPATIBLE_NAMES = {
    "ambrose",
    "ansel",
    "arthur",
    "bennett",
    "calvin",
    "cassian",
    "dashiell",
    "emil",
    "felix",
    "finnian",
    "gideon",
    "graham",
    "harlan",
    "hugo",
    "jasper",
    "jonah",
    "julian",
    "kieran",
    "leif",
    "luca",
    "matteo",
    "micah",
    "miles",
    "nico",
    "otto",
    "owen",
    "rafael",
    "reid",
    "rhys",
    "silas",
    "soren",
    "stellan",
    "theo",
    "tobias",
    "xavier",
}

BABY_BOY_INCOMPATIBLE_NAMES = {
    "ada",
    "alma",
    "amara",
    "anouk",
    "anya",
    "aurelia",
    "beatrice",
    "blythe",
    "calla",
    "celia",
    "clara",
    "cora",
    "dalia",
    "daphne",
    "elodie",
    "eloise",
    "esme",
    "flora",
    "freya",
    "greta",
    "ida",
    "imogen",
    "iris",
    "ivy",
    "june",
    "lena",
    "leona",
    "liora",
    "louisa",
    "lyra",
    "mabel",
    "maeve",
    "maren",
    "margot",
    "maya",
    "mira",
    "nina",
    "noemi",
    "nora",
    "opal",
    "orla",
    "petra",
    "phoebe",
    "rhea",
    "romy",
    "serena",
    "sylvie",
    "tessa",
    "thea",
    "vera",
    "willa",
    "zara",
}


def validate_result(
    vertical: VerticalConfig,
    brief: NamingBrief,
    result: NameResult,
) -> list[ValidationResult]:
    if vertical.slug == "pet":
        return _validate_pet_name(brief, result.name)
    if vertical.slug == "baby":
        return _validate_baby_name(brief, result.name)
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
    results = filter_results_for_brief(vertical, brief, results)
    for result in results:
        result.validation = validate_result(vertical, brief, result)
        result.scores.update(_scores_from_validation(result.validation))
    return results


def filter_results_for_brief(
    vertical: VerticalConfig,
    brief: NamingBrief,
    results: list[NameResult],
) -> list[NameResult]:
    if vertical.slug != "baby":
        return results

    return [result for result in results if is_baby_name_allowed_for_gender(brief, result.name)]


def is_baby_name_allowed_for_gender(brief: NamingBrief, name: str) -> bool:
    gender = str(brief.inputs.get("gender", "")).strip().lower()
    clean_name = _clean_name_key(name)
    if gender == "girl":
        return clean_name not in BABY_GIRL_INCOMPATIBLE_NAMES
    if gender == "boy":
        return clean_name not in BABY_BOY_INCOMPATIBLE_NAMES
    return True


def _validate_pet_name(brief: NamingBrief, name: str) -> list[ValidationResult]:
    clean_name = _clean_name_key(name)
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


def _validate_baby_name(brief: NamingBrief, name: str) -> list[ValidationResult]:
    clean_name = _clean_name_key(name)
    avoid = {item.lower() for item in brief.avoid}
    syllable_count = _estimate_syllables(clean_name)
    validation = [
        _baby_pronunciation_validation(clean_name, syllable_count),
        _baby_initials_validation(brief, clean_name),
        _baby_popularity_validation(clean_name),
    ]
    if avoid:
        validation.append(_pet_avoid_validation(clean_name, avoid))
    return validation


def _baby_pronunciation_validation(clean_name: str, syllable_count: int) -> ValidationResult:
    if 1 <= syllable_count <= 3 and len(clean_name) <= 8:
        return ValidationResult(
            module="baby_pronunciation",
            status=ValidationStatus.PASS,
            label="Pronunciation",
            message="Readable sound shape for everyday introductions.",
            score=0.9,
            confidence=0.82,
            metadata={"length": len(clean_name), "syllables": syllable_count},
        )
    return ValidationResult(
        module="baby_pronunciation",
        status=ValidationStatus.WARN,
        label="Pronunciation",
        message="A little longer or less immediate; test how people read it cold.",
        score=0.72,
        confidence=0.76,
        metadata={"length": len(clean_name), "syllables": syllable_count},
    )


def _baby_initials_validation(brief: NamingBrief, clean_name: str) -> ValidationResult:
    family_context = str(brief.inputs.get("family_context", "")).strip()
    if not family_context:
        return ValidationResult(
            module="baby_initials",
            status=ValidationStatus.UNKNOWN,
            label="Initials",
            message="Add a surname or initials to check full-name flow.",
            score=0.62,
            confidence=0.58,
        )
    return ValidationResult(
        module="baby_initials",
        status=ValidationStatus.PASS,
        label="Initials",
        message="Family context provided; test the full name out loud before deciding.",
        score=0.84,
        confidence=0.7,
        metadata={"first_initial": clean_name[:1].upper()},
    )


def _baby_popularity_validation(clean_name: str) -> ValidationResult:
    familiar_names = {"maya", "nora", "theo", "miles", "clara"}
    if clean_name in familiar_names:
        return ValidationResult(
            module="baby_popularity",
            status=ValidationStatus.WARN,
            label="Popularity",
            message="Familiar choice; decide whether that comfort is a plus or a concern.",
            score=0.72,
            confidence=0.65,
        )
    return ValidationResult(
        module="baby_popularity",
        status=ValidationStatus.PASS,
        label="Popularity",
        message="Distinctive enough to feel considered without being hard to use.",
        score=0.84,
        confidence=0.65,
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


def _clean_name_key(name: str) -> str:
    return "".join(character for character in name.lower() if character.isalpha())


def _scores_from_validation(validation: list[ValidationResult]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for item in validation:
        if item.score is not None:
            scores[item.module] = item.score
    return scores
