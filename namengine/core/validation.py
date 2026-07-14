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
    "aarav",
    "akio",
    "alejandro",
    "alessio",
    "alfred",
    "alistair",
    "amari",
    "ambrose",
    "an",
    "anders",
    "andreas",
    "andres",
    "ansel",
    "anselm",
    "aram",
    "arda",
    "ari",
    "arjun",
    "arman",
    "arthur",
    "asher",
    "ashot",
    "axel",
    "banjo",
    "bao",
    "bastien",
    "bayan",
    "bayard",
    "bennett",
    "bohdan",
    "booker",
    "bram",
    "bryn",
    "cai",
    "caio",
    "callum",
    "calvin",
    "cassian",
    "cillian",
    "clancy",
    "cormac",
    "cyrus",
    "daan",
    "dakota",
    "dante",
    "danylo",
    "darcy",
    "darius",
    "dashiell",
    "declan",
    "deniz",
    "dev",
    "diego",
    "dimitri",
    "dmitri",
    "dohyun",
    "duarte",
    "duc",
    "duncan",
    "dylan",
    "eamon",
    "edmund",
    "einar",
    "eitan",
    "elian",
    "elio",
    "ellington",
    "emil",
    "emiliano",
    "emilio",
    "emir",
    "emrys",
    "enzo",
    "etienne",
    "ewan",
    "ezra",
    "felix",
    "finnian",
    "floris",
    "frederick",
    "fritz",
    "gideon",
    "giovanni",
    "graham",
    "hamish",
    "harlan",
    "haru",
    "hayk",
    "heinrich",
    "hiro",
    "hugh",
    "hugo",
    "hyun",
    "idris",
    "ivan",
    "janek",
    "jasper",
    "javier",
    "jett",
    "jian",
    "jiho",
    "joao",
    "jonah",
    "joon",
    "jose",
    "julian",
    "kai",
    "kazimir",
    "kenji",
    "kerem",
    "khoa",
    "kian",
    "kieran",
    "kiran",
    "klaus",
    "kofi",
    "kwame",
    "lachie",
    "lachlan",
    "langston",
    "lars",
    "leander",
    "leif",
    "leonardo",
    "lev",
    "levent",
    "levko",
    "levon",
    "liang",
    "linus",
    "lito",
    "lorenzo",
    "luca",
    "lucas",
    "lucien",
    "lukasz",
    "luther",
    "magnus",
    "malcolm",
    "marcel",
    "marco",
    "marek",
    "mateo",
    "mateus",
    "matteo",
    "micah",
    "miguel",
    "mika",
    "mikhail",
    "mikkel",
    "miles",
    "ming",
    "minh",
    "minjun",
    "mykola",
    "navid",
    "ned",
    "nico",
    "niels",
    "nikhil",
    "nikolai",
    "nikos",
    "nils",
    "noam",
    "nodin",
    "nuno",
    "omar",
    "omari",
    "ostap",
    "otto",
    "owain",
    "owen",
    "ozan",
    "pascal",
    "percy",
    "pieter",
    "piotr",
    "quang",
    "rafael",
    "rafi",
    "rami",
    "ramon",
    "reid",
    "remy",
    "ren",
    "rhys",
    "rocco",
    "rohan",
    "ronan",
    "rostam",
    "rupert",
    "samir",
    "sander",
    "santiago",
    "santino",
    "seamus",
    "seojoon",
    "silas",
    "sora",
    "soren",
    "stelios",
    "stellan",
    "suren",
    "sven",
    "tadeusz",
    "tahoma",
    "takoda",
    "taras",
    "tariq",
    "theo",
    "thiago",
    "thijs",
    "thurgood",
    "tiago",
    "tigran",
    "tobias",
    "viktor",
    "vittorio",
    "wei",
    "winston",
    "xavier",
    "yuma",
    "zayn",
    "zuberi",
}

BABY_BOY_INCOMPATIBLE_NAMES = {
    "aaliyah",
    "ada",
    "alma",
    "amara",
    "amina",
    "anouk",
    "anya",
    "asha",
    "aurelia",
    "ayana",
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
    "eshe",
    "esme",
    "flora",
    "freya",
    "greta",
    "ida",
    "imogen",
    "iris",
    "imani",
    "ivy",
    "june",
    "kenya",
    "lena",
    "leona",
    "liora",
    "louisa",
    "lyra",
    "mabel",
    "maeve",
    "makena",
    "maren",
    "margot",
    "maya",
    "mira",
    "nia",
    "nina",
    "noemi",
    "nora",
    "opal",
    "orla",
    "petra",
    "phoebe",
    "rhea",
    "romy",
    "sanaa",
    "serena",
    "sylvie",
    "tessa",
    "thea",
    "vera",
    "willa",
    "zahara",
    "zara",
    "zora",
    "zuri",
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
    if vertical.slug == "business":
        return _validate_business_name(brief, result.name)
    if vertical.slug == "product":
        return _validate_product_name(brief, result.name)
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

    return [
        result
        for result in results
        if is_baby_name_allowed_for_gender(brief, result.name)
        and not is_name_explicitly_avoided(brief, result.name)
    ]


def is_baby_name_allowed_for_gender(brief: NamingBrief, name: str) -> bool:
    gender = str(brief.inputs.get("gender", "")).strip().lower()
    clean_name = _clean_name_key(name)
    if gender == "girl":
        return clean_name not in BABY_GIRL_INCOMPATIBLE_NAMES
    if gender == "boy":
        return clean_name not in BABY_BOY_INCOMPATIBLE_NAMES
    return True


def is_name_explicitly_avoided(brief: NamingBrief, name: str) -> bool:
    clean_name = _clean_name_key(name)
    avoid = {_clean_name_key(item) for item in brief.avoid}
    return clean_name in avoid


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
        _baby_gender_direction_validation(brief, clean_name),
        _baby_pronunciation_validation(clean_name, syllable_count),
        _baby_initials_validation(brief, clean_name),
        _baby_popularity_validation(clean_name),
    ]
    if avoid:
        validation.append(_pet_avoid_validation(clean_name, avoid))
    return validation


def _validate_business_name(brief: NamingBrief, name: str) -> list[ValidationResult]:
    clean_name = _clean_name_key(name)
    avoid = {_clean_name_key(item) for item in brief.avoid}
    validation = [
        _business_domain_validation(clean_name, name),
        _business_category_fit_validation(brief),
        _business_similarity_validation(brief, clean_name),
    ]
    if avoid:
        validation.append(_business_avoid_validation(clean_name, avoid))
    return validation


def _business_domain_validation(clean_name: str, display_name: str) -> ValidationResult:
    has_ampersand = "&" in display_name
    if 4 <= len(clean_name) <= 13 and not has_ampersand:
        return ValidationResult(
            module="business_domain",
            status=ValidationStatus.PASS,
            label="Domain signal",
            message="Compact enough to test as a domain or social handle.",
            score=0.84,
            confidence=0.68,
            metadata={"letters": len(clean_name)},
        )
    return ValidationResult(
        module="business_domain",
        status=ValidationStatus.WARN,
        label="Domain signal",
        message="Test modifiers, punctuation, and handle fit before launch.",
        score=0.64,
        confidence=0.66,
        metadata={"letters": len(clean_name)},
    )


def _business_category_fit_validation(brief: NamingBrief) -> ValidationResult:
    industry = str(brief.inputs.get("industry", "")).strip()
    description = str(brief.inputs.get("business_description", "")).strip()
    if industry or description:
        return ValidationResult(
            module="business_category_fit",
            status=ValidationStatus.PASS,
            label="Category fit",
            message="Business context is present; judge whether the name signals the right lane.",
            score=0.82,
            confidence=0.7,
            metadata={"has_industry": bool(industry), "has_description": bool(description)},
        )
    return ValidationResult(
        module="business_category_fit",
        status=ValidationStatus.UNKNOWN,
        label="Category fit",
        message="Add industry or offer context to check category fit more clearly.",
        score=0.55,
        confidence=0.55,
    )


def _business_similarity_validation(
    brief: NamingBrief,
    clean_name: str,
) -> ValidationResult:
    avoid = {_clean_name_key(item) for item in brief.avoid}
    if clean_name in avoid:
        return ValidationResult(
            module="business_similarity",
            status=ValidationStatus.FAIL,
            label="Launch risk",
            message="This appears in the avoid list and should not move forward.",
            score=0.0,
            confidence=0.92,
        )
    return ValidationResult(
        module="business_similarity",
        status=ValidationStatus.WARN,
        label="Launch risk",
        message="Do trademark, competitor, domain, and social checks before committing.",
        score=0.62,
        confidence=0.7,
    )


def _business_avoid_validation(clean_name: str, avoid: set[str]) -> ValidationResult:
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


def _validate_product_name(brief: NamingBrief, name: str) -> list[ValidationResult]:
    clean_name = _clean_name_key(name)
    avoid = {_clean_name_key(item) for item in brief.avoid}
    validation = [
        _product_shelf_fit_validation(clean_name, name),
        _product_category_fit_validation(brief),
        _product_claim_risk_validation(brief, clean_name),
    ]
    if avoid:
        validation.append(_business_avoid_validation(clean_name, avoid))
    return validation


def _product_shelf_fit_validation(clean_name: str, display_name: str) -> ValidationResult:
    has_ampersand = "&" in display_name
    if 4 <= len(clean_name) <= 13 and not has_ampersand:
        return ValidationResult(
            module="product_shelf_fit",
            status=ValidationStatus.PASS,
            label="Shelf fit",
            message="Compact enough to test on packaging, thumbnails, and short listings.",
            score=0.84,
            confidence=0.7,
            metadata={"letters": len(clean_name)},
        )
    return ValidationResult(
        module="product_shelf_fit",
        status=ValidationStatus.WARN,
        label="Shelf fit",
        message="Test small-label readability, SKU fit, and marketplace display before launch.",
        score=0.64,
        confidence=0.66,
        metadata={"letters": len(clean_name)},
    )


def _product_category_fit_validation(brief: NamingBrief) -> ValidationResult:
    category = str(brief.inputs.get("category", "")).strip()
    description = str(brief.inputs.get("product_description", "")).strip()
    if category or description:
        return ValidationResult(
            module="product_category_fit",
            status=ValidationStatus.PASS,
            label="Category fit",
            message="Product context is present; judge whether the name signals the right buying lane.",
            score=0.82,
            confidence=0.7,
            metadata={"has_category": bool(category), "has_description": bool(description)},
        )
    return ValidationResult(
        module="product_category_fit",
        status=ValidationStatus.UNKNOWN,
        label="Category fit",
        message="Add product category or description to check fit more clearly.",
        score=0.55,
        confidence=0.55,
    )


def _product_claim_risk_validation(brief: NamingBrief, clean_name: str) -> ValidationResult:
    avoid = {_clean_name_key(item) for item in brief.avoid}
    if clean_name in avoid:
        return ValidationResult(
            module="product_claim_risk",
            status=ValidationStatus.FAIL,
            label="Launch risk",
            message="This appears in the avoid list and should not move forward.",
            score=0.0,
            confidence=0.92,
        )
    return ValidationResult(
        module="product_claim_risk",
        status=ValidationStatus.WARN,
        label="Launch risk",
        message="Check trademark, regulated claims, competitor similarity, and channel rules before committing.",
        score=0.62,
        confidence=0.7,
    )


def _baby_gender_direction_validation(
    brief: NamingBrief,
    clean_name: str,
) -> ValidationResult:
    gender = str(brief.inputs.get("gender", "")).strip().lower()
    if gender == "girl" and clean_name in BABY_GIRL_INCOMPATIBLE_NAMES:
        return ValidationResult(
            module="baby_gender_direction",
            status=ValidationStatus.FAIL,
            label="Gender direction",
            message="This reads masculine for a Girl search and should not be shown.",
            score=0.0,
            confidence=0.96,
            metadata={"gender": "Girl"},
        )
    if gender == "boy" and clean_name in BABY_BOY_INCOMPATIBLE_NAMES:
        return ValidationResult(
            module="baby_gender_direction",
            status=ValidationStatus.FAIL,
            label="Gender direction",
            message="This reads feminine for a Boy search and should not be shown.",
            score=0.0,
            confidence=0.96,
            metadata={"gender": "Boy"},
        )
    if gender in {"girl", "boy"}:
        message = f"Compatible with the requested {gender.title()} direction."
    else:
        message = "Flexible for the requested naming direction."
    return ValidationResult(
        module="baby_gender_direction",
        status=ValidationStatus.PASS,
        label="Gender direction",
        message=message,
        score=0.9,
        confidence=0.82,
        metadata={"gender": gender or "unspecified"},
    )


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
