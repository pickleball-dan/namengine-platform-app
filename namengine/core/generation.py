"""Shared generation interface for NamEngine."""

from __future__ import annotations

import re

from namengine.core.schemas import (
    NameResult,
    NamingBrief,
    TasteProfile,
    VerticalConfig,
)
from namengine.core.validation import validate_results


PET_NAME_POOL = [
    ("Milo", "MY-loh", "Friendly, bright, and easy to call."),
    ("Juniper", "JOO-nuh-per", "Nature-leaning with a warm, lively shape."),
    ("Rory", "ROR-ee", "Bouncy, clear, and cheerful without feeling silly."),
    ("Clover", "KLOH-ver", "Soft, lucky, and sweet with outdoor charm."),
    ("Toby", "TOH-bee", "Familiar, loyal, and simple across a room."),
    ("Sierra", "see-AIR-uh", "Open-air, graceful, and calm."),
    ("Maple", "MAY-pul", "Cozy, gentle, and affectionate."),
    ("Finn", "FIN", "Short, crisp, and highly callable."),
]

PET_REFINED_POOL = [
    ("Benny", "BEN-ee", "Sunny, familiar, and affectionate."),
    ("Scout", "SKOWT", "Adventurous and crisp without trying too hard."),
    ("Poppy", "POP-ee", "Bright, sweet, and easy to call."),
    ("Ollie", "AH-lee", "Friendly and playful with a soft landing."),
    ("Winnie", "WIN-ee", "Gentle, cozy, and lovable."),
    ("Remy", "REM-ee", "Warm, stylish, and still pet-ready."),
    ("Sunny", "SUN-ee", "Happy, direct, and hard to misunderstand."),
    ("Hazel", "HAY-zul", "Soft, nature-touched, and grounded."),
]

PET_FINALIST_POOL = [
    ("Milo", "MY-loh", "Friendly, bright, and easy to call."),
    ("Rory", "ROR-ee", "Bouncy, clear, and cheerful without feeling silly."),
    ("Scout", "SKOWT", "Adventurous and crisp without trying too hard."),
    ("Poppy", "POP-ee", "Bright, sweet, and easy to call."),
    ("Remy", "REM-ee", "Warm, stylish, and still pet-ready."),
    ("Hazel", "HAY-zul", "Soft, nature-touched, and grounded."),
]


def slugify(value: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return clean or "name"


def _brief_text(brief: NamingBrief, key: str, default: str = "") -> str:
    value = brief.inputs.get(key, default)
    return str(value).strip()


def _pet_fit_note(name: str, species: str, personality: str) -> str:
    animal = species or "pet"
    if personality:
        return f"Best for a {animal} with a {personality.lower()} streak."
    return f"Best for a {animal} that needs a name people can say easily."


def generate_names(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int = 1,
    taste_summary: str = "",
    taste_profile: TasteProfile | None = None,
    previous_names: list[str] | None = None,
    use_ai: bool = True,
) -> list[NameResult]:
    if vertical.slug != "pet":
        raise NotImplementedError("Phase 3 only generates Pet results.")

    if use_ai:
        from namengine.core.model_router import generate_with_router

        routed = generate_with_router(
            vertical=vertical,
            brief=brief,
            round_number=round_number,
            taste_profile=taste_profile,
            previous_names=previous_names or [],
        )
        if routed:
            return routed

    return generate_fallback_names(
        vertical=vertical,
        brief=brief,
        round_number=round_number,
        taste_summary=taste_summary,
    )


def generate_fallback_names(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int = 1,
    taste_summary: str = "",
) -> list[NameResult]:
    species = _brief_text(brief, "pet_type") or _brief_text(brief, "species", "pet")
    personality = _brief_text(brief, "vibe") or _brief_text(brief, "personality")
    style = _brief_text(brief, "style", "warm and wearable")
    avoid_text = ", ".join(brief.avoid)

    pool = PET_NAME_POOL
    if round_number == 2:
        pool = PET_REFINED_POOL
    elif round_number >= 3:
        pool = PET_FINALIST_POOL

    results: list[NameResult] = []
    for index, (name, pronunciation, opener) in enumerate(pool, start=1):
        result_id = f"{vertical.slug}-{index}"
        risks = []
        if name.lower() in {item.lower() for item in brief.avoid}:
            risks.append("This name matches something in the avoid list.")
        if len(name) > 8:
            risks.append("Slightly longer name; test how it feels when called.")

        if not risks:
            risks.append("Low practical risk; still test it out loud.")

        why = (
            f"{name} fits the {style.lower()} lane while staying easy to remember. "
            f"It gives a {species.lower()} name enough personality without making it hard to call."
        )
        if taste_summary:
            why += f" {taste_summary}"
        if avoid_text:
            why += f" It also stays mindful of your avoid list: {avoid_text}."

        results.append(
            NameResult(
                id=result_id,
                name=name,
                slug=slugify(name),
                pronunciation=pronunciation,
                tagline=opener,
                meaning="A wearable pet name shaped for callability and warmth.",
                why_this_name=why,
                fit_note=_pet_fit_note(name, species, personality),
                risks=risks,
                tags=["callable", "warm", "pet-ready"],
                scores={
                    "callability": 0.92 if len(name) <= 5 else 0.84,
                    "warmth": 0.88,
                    "distinctiveness": 0.62 if name in {"Milo", "Toby", "Finn"} else 0.76,
                },
                metadata={"source": "phase3_fallback", "round_number": round_number},
            )
        )

    if round_number >= 3:
        return validate_results(vertical, brief, results[:6])
    return validate_results(vertical, brief, results[: vertical.default_result_count])
