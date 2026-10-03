"""Read-only capability contracts for active NamEngine verticals."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from namengine.core.generation_prompt_config import (
    GenerationPromptConfig,
    generation_prompt_config_or_none,
)
from namengine.core.pet_portrait import ArtifactDefinition, artifact_definition_or_none
from namengine.core.quality_framework import QualityAdapter, quality_adapter_for
from namengine.core.schemas import NameResult, NamingBrief, VerticalConfig
from namengine.core.validation import validate_result


ACTIVE_VERTICAL_SLUGS: tuple[str, ...] = ("baby", "pet", "business", "boat")

SPECIAL_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "baby": ("baby_taxonomy", "baby_final_decision"),
    "pet": ("pet_legacy_brief_aliases",),
    "business": ("business_recovery_finalizer", "business_domain_enrichment"),
    "boat": ("boat_transom_artifact",),
}


class CapabilityContractError(RuntimeError):
    """Raised when an active vertical is missing a required subsystem contract."""


@dataclass(frozen=True, slots=True)
class VerticalCapabilityContract:
    vertical_slug: str
    review_mode: str
    max_rounds: int
    terminal_reaction_mode: str
    terminal_edit_locked: bool
    generation_prompt_config: GenerationPromptConfig
    quality_adapter: QualityAdapter
    validation_modules: tuple[str, ...]
    validation_executor_modules: tuple[str, ...]
    artifact_definition: ArtifactDefinition
    special_capabilities: tuple[str, ...] = ()

    @property
    def artifact_kind(self) -> str:
        return self.artifact_definition.kind

    @property
    def artifact_render_variant(self) -> str:
        return self.artifact_definition.render_variant


QualityLookup = Callable[[str], QualityAdapter | None]
GenerationPromptLookup = Callable[[str], GenerationPromptConfig | None]
ArtifactLookup = Callable[[str], ArtifactDefinition | None]


def vertical_capability_contract(
    vertical: VerticalConfig,
    *,
    generation_lookup: GenerationPromptLookup = generation_prompt_config_or_none,
    quality_lookup: QualityLookup = quality_adapter_for,
    artifact_lookup: ArtifactLookup = artifact_definition_or_none,
) -> VerticalCapabilityContract:
    """Aggregate the current subsystem registrations for one active vertical."""

    slug = vertical.slug.strip().lower()
    generation_config = generation_lookup(slug)
    if generation_config is None:
        raise CapabilityContractError(
            f"Generation prompt config is not registered for active vertical: {slug}"
        )

    _ensure_builtin_quality_adapters_registered()
    quality_adapter = quality_lookup(slug)
    if quality_adapter is None:
        raise CapabilityContractError(
            f"Quality adapter is not registered for active vertical: {slug}"
        )

    validation_modules = tuple(vertical.validation_modules)
    if not validation_modules:
        raise CapabilityContractError(
            f"Validation modules are not declared for active vertical: {slug}"
        )
    executor_modules = _validation_executor_modules(vertical)
    if "validation_not_configured" in executor_modules:
        raise CapabilityContractError(
            f"Validation executor is not configured for active vertical: {slug}"
        )

    artifact_definition = artifact_lookup(slug)
    if artifact_definition is None:
        raise CapabilityContractError(
            f"Graphical artifact is not registered for active vertical: {slug}"
        )

    return VerticalCapabilityContract(
        vertical_slug=slug,
        review_mode=vertical.review_mode,
        max_rounds=vertical.max_rounds,
        terminal_reaction_mode=vertical.terminal_reaction_mode,
        terminal_edit_locked=vertical.terminal_edit_locked,
        generation_prompt_config=generation_config,
        quality_adapter=quality_adapter,
        validation_modules=validation_modules,
        validation_executor_modules=executor_modules,
        artifact_definition=artifact_definition,
        special_capabilities=SPECIAL_CAPABILITIES.get(slug, ()),
    )


def active_vertical_capability_contracts(
    active_verticals: Iterable[VerticalConfig] | None = None,
    *,
    generation_lookup: GenerationPromptLookup = generation_prompt_config_or_none,
    quality_lookup: QualityLookup = quality_adapter_for,
    artifact_lookup: ArtifactLookup = artifact_definition_or_none,
) -> tuple[VerticalCapabilityContract, ...]:
    verticals = tuple(active_verticals) if active_verticals is not None else active_verticals_for_contract()
    return tuple(
        vertical_capability_contract(
            vertical,
            generation_lookup=generation_lookup,
            quality_lookup=quality_lookup,
            artifact_lookup=artifact_lookup,
        )
        for vertical in verticals
    )


def assert_active_vertical_capability_contracts_complete(
    active_verticals: Iterable[VerticalConfig] | None = None,
) -> tuple[VerticalCapabilityContract, ...]:
    """Fail fast if any active vertical depends on a silent subsystem fallback."""

    return active_vertical_capability_contracts(active_verticals)


def active_verticals_for_contract() -> tuple[VerticalConfig, ...]:
    from namengine.verticals.configs import VERTICALS

    return tuple(VERTICALS[slug] for slug in ACTIVE_VERTICAL_SLUGS)


def _ensure_builtin_quality_adapters_registered() -> None:
    import namengine.core.quality_adapters  # noqa: F401


def _validation_executor_modules(vertical: VerticalConfig) -> tuple[str, ...]:
    brief = NamingBrief(vertical=vertical.slug, inputs={})
    result = NameResult(id=f"{vertical.slug}-contract-probe", name="Contract", slug="contract")
    return tuple(item.module for item in validate_result(vertical, brief, result))
