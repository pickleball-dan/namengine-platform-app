"""Explicit generation prompt configuration by vertical."""

from __future__ import annotations

from dataclasses import dataclass

from namengine.core.prompt_versions import (
    BABY_PROMPT_VERSION,
    BUSINESS_PROMPT_VERSION,
    DEFAULT_PROMPT_VERSION,
    PET_PROMPT_VERSION,
)


DEFAULT_MODEL_SCORE_KEYS = ("callability", "warmth", "distinctiveness")


@dataclass(frozen=True, slots=True)
class GenerationPromptConfig:
    vertical_slug: str
    prompt_version: str
    model_score_keys: tuple[str, ...] = DEFAULT_MODEL_SCORE_KEYS
    prompt_guidance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.vertical_slug or self.vertical_slug != self.vertical_slug.strip().lower():
            raise ValueError("Generation prompt config slugs must be non-empty lowercase values")
        if not self.prompt_version.strip():
            raise ValueError("Generation prompt configs require a prompt version")
        if not self.model_score_keys or len(set(self.model_score_keys)) != len(self.model_score_keys):
            raise ValueError("Generation prompt config score keys must be non-empty and unique")


_GENERATION_PROMPT_CONFIGS: dict[str, GenerationPromptConfig] = {
    "baby": GenerationPromptConfig(
        vertical_slug="baby",
        prompt_version=BABY_PROMPT_VERSION,
        model_score_keys=(
            "fit",
            "usability",
            "distinctiveness",
            "cultural_alignment",
            "sound",
            "explanation_quality",
        ),
        prompt_guidance=(
            "Explain why each name fits this specific parent brief, not only its meaning.",
            "Mention a relevant tradeoff honestly and keep the explanation concise.",
            "Use varied, parent-friendly phrasing across the list.",
            "Treat model scores as evidence; the application makes the final rank.",
        ),
    ),
    "pet": GenerationPromptConfig(
        vertical_slug="pet",
        prompt_version=PET_PROMPT_VERSION,
        model_score_keys=DEFAULT_MODEL_SCORE_KEYS,
        prompt_guidance=(
            "Keep every Pet-specific intake field as evidence; do not genericize into Baby naming language.",
            "Prioritize callability, animal personality, and household fit over abstract name beauty.",
            "Tie the rationale to the pet type, personality, style, and practical out-loud use.",
            "Mention one practical tradeoff honestly when relevant.",
        ),
    ),
    "business": GenerationPromptConfig(
        vertical_slug="business",
        prompt_version=BUSINESS_PROMPT_VERSION,
        model_score_keys=("memorability", "category_fit", "launch_readiness"),
        prompt_guidance=(
            "Business explanations must tie the name to the offer, audience, category, and launch risk.",
            "Scores must evaluate memorability, category_fit, and launch_readiness instead of baby/pet warmth.",
            "Treat domain, social handle, trademark, and competitor checks as practical risks, not guarantees.",
        ),
    ),
    "boat": GenerationPromptConfig(
        vertical_slug="boat",
        prompt_version=DEFAULT_PROMPT_VERSION,
        model_score_keys=DEFAULT_MODEL_SCORE_KEYS,
        prompt_guidance=(),
    ),
}


def generation_prompt_config_for(vertical_slug: str) -> GenerationPromptConfig:
    slug = vertical_slug.strip().lower()
    return _GENERATION_PROMPT_CONFIGS.get(
        slug,
        GenerationPromptConfig(vertical_slug=slug or "default", prompt_version=DEFAULT_PROMPT_VERSION),
    )


def generation_prompt_config_or_none(vertical_slug: str) -> GenerationPromptConfig | None:
    return _GENERATION_PROMPT_CONFIGS.get(vertical_slug.strip().lower())


def generation_prompt_version_for(vertical_slug: str) -> str:
    return generation_prompt_config_for(vertical_slug).prompt_version


def generation_model_score_keys(vertical_slug: str) -> tuple[str, ...]:
    return generation_prompt_config_for(vertical_slug).model_score_keys


def generation_prompt_guidance(vertical_slug: str) -> tuple[str, ...]:
    return generation_prompt_config_for(vertical_slug).prompt_guidance


def registered_generation_prompt_configs() -> dict[str, GenerationPromptConfig]:
    return dict(_GENERATION_PROMPT_CONFIGS)
