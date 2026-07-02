"""User-facing generation progress and trust cues."""

from __future__ import annotations

from namengine.core.schemas import NameResult


PROGRESS_STEPS = (
    "Reading your brief",
    "Finding strong first options",
    "Checking fit and callability",
    "Comparing naming strategies",
    "Selecting the strongest names",
)


def build_trust_cue(names: list[NameResult]) -> dict[str, object]:
    providers = {
        str(item.metadata.get("provider") or item.metadata.get("source") or "unknown")
        for item in names
    }
    validation_count = sum(len(item.validation) for item in names)
    candidate_count = max(
        len(names),
        sum(int(item.metadata.get("candidate_count", 1)) for item in names),
    )
    traits = ["fit"]
    if validation_count:
        traits.append("callability")
    if any(item.scores.get("distinctiveness") for item in names):
        traits.append("distinctiveness")

    return {
        "candidate_count": candidate_count,
        "provider_count": len(providers),
        "validation_count": validation_count,
        "traits": traits,
        "summary": _summary(candidate_count, validation_count, traits),
    }


def _summary(
    candidate_count: int,
    validation_count: int,
    traits: list[str],
) -> str:
    if validation_count:
        return (
            f"Selected from {candidate_count} candidates and filtered for "
            f"{', '.join(traits)}."
        )
    return f"Selected from {candidate_count} candidates matched to your brief."
