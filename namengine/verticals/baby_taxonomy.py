"""Authoritative executable taxonomy for the Baby recommendation engine.

Baby Taxonomy v1 owns the stable intake vocabulary and its compatibility
surface. Engine consumers should import this module instead of maintaining
parallel Baby option lists or legacy aliases.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


BABY_TAXONOMY_VERSION = "baby-taxonomy-v1"


@dataclass(frozen=True, slots=True)
class BabyTaxonomyField:
    """One Baby intake field and the choice labels accepted for Taxonomy v1."""

    field_id: str
    current_choices: tuple[str, ...] = ()
    legacy_choices: tuple[str, ...] = ()
    deprecated_aliases: tuple[str, ...] = ()
    prompt_key: str = ""

    @property
    def accepted_choices(self) -> tuple[str, ...]:
        return self.current_choices + self.legacy_choices

    def resolve_choice(self, value: str) -> str | None:
        """Return the exact registered label for a case-insensitive input."""
        normalized = _normalize(value)
        return next(
            (choice for choice in self.accepted_choices if _normalize(choice) == normalized),
            None,
        )

    def project_prompt_value(self, value: Any) -> str:
        """Project accepted input to its registered prompt label without rewording."""
        text = str(value or "").strip()
        if not text:
            return ""
        return self.resolve_choice(text) or text


@dataclass(frozen=True, slots=True)
class BabyTaxonomy:
    """Versioned Baby vocabulary with lookup and compatibility helpers."""

    version: str
    fields: tuple[BabyTaxonomyField, ...]
    legacy_migration_aliases: tuple[tuple[str, str], ...]
    migration_metadata_aliases: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.version != BABY_TAXONOMY_VERSION:
            raise ValueError("Unsupported Baby taxonomy version")

        field_ids = [field.field_id for field in self.fields]
        if len(field_ids) != len(set(field_ids)):
            raise ValueError("Baby taxonomy field IDs must be unique")

        lookup_keys: list[str] = []
        for field in self.fields:
            if not field.field_id or field.field_id != field.field_id.strip().lower():
                raise ValueError("Baby taxonomy field IDs must be lowercase")
            accepted = field.accepted_choices
            if len({_normalize(choice) for choice in accepted}) != len(accepted):
                raise ValueError(f"Baby taxonomy choices must be unique for {field.field_id}")
            lookup_keys.extend((field.field_id, *field.deprecated_aliases))

        normalized_keys = [_normalize(key) for key in lookup_keys]
        if len(normalized_keys) != len(set(normalized_keys)):
            raise ValueError("Baby taxonomy field aliases must be unambiguous")

        prompt_keys = [field.prompt_key for field in self.fields if field.prompt_key]
        if len(prompt_keys) != len(set(prompt_keys)):
            raise ValueError("Baby taxonomy prompt keys must be unique")

        known_fields = set(field_ids)
        for alias, field_id in self.legacy_migration_aliases + self.migration_metadata_aliases:
            if not alias or field_id not in known_fields:
                raise ValueError("Baby taxonomy migration aliases must target known fields")

    def field(self, field_or_alias: str) -> BabyTaxonomyField:
        field_id = self.resolve_field_id(field_or_alias)
        if field_id is None:
            raise KeyError(field_or_alias)
        return next(field for field in self.fields if field.field_id == field_id)

    def resolve_field_id(self, field_or_alias: str) -> str | None:
        """Resolve a canonical field ID or any registered deprecated alias."""
        normalized = _normalize(field_or_alias)
        for field in self.fields:
            if normalized in {
                _normalize(field.field_id),
                *(_normalize(alias) for alias in field.deprecated_aliases),
            }:
                return field.field_id
        return None

    def current_choices(self, field_or_alias: str) -> tuple[str, ...]:
        return self.field(field_or_alias).current_choices

    def accepted_choices(self, field_or_alias: str) -> tuple[str, ...]:
        return self.field(field_or_alias).accepted_choices

    def deprecated_aliases(self, field_id: str) -> tuple[str, ...]:
        return self.field(field_id).deprecated_aliases

    def resolve_choice(self, field_or_alias: str, value: str) -> str | None:
        return self.field(field_or_alias).resolve_choice(value)

    def project_prompt_value(self, field_or_alias: str, value: Any) -> str:
        return self.field(field_or_alias).project_prompt_value(value)

    def prompt_projection(self, inputs: Mapping[str, Any]) -> dict[str, str]:
        """Return the six canonical Baby taste axes used by AI prompt builders."""
        return {
            field.prompt_key: field.project_prompt_value(inputs.get(field.field_id))
            for field in self.fields
            if field.prompt_key
        }

    def legacy_migration_mapping(self) -> dict[str, str]:
        return dict(self.legacy_migration_aliases)

    def migration_metadata_mapping(self) -> dict[str, str]:
        return dict(self.migration_metadata_aliases)


def _normalize(value: str) -> str:
    return " ".join(str(value).strip().casefold().split())


BABY_TAXONOMY = BabyTaxonomy(
    version=BABY_TAXONOMY_VERSION,
    fields=(
        BabyTaxonomyField(
            "gender",
            current_choices=("Girl", "Boy", "Gender-neutral", "Surprise me"),
            deprecated_aliases=("baby_gender", "sex"),
        ),
        BabyTaxonomyField("family_context", deprecated_aliases=("family",)),
        BabyTaxonomyField(
            "cultural_heritage",
            current_choices=(
                "No preference",
                "African",
                "African American",
                "Arab / Middle Eastern",
                "Armenian",
                "Australian",
                "Brazilian",
                "Chinese",
                "Danish",
                "Dutch",
                "English",
                "Filipino",
                "French",
                "German",
                "Greek",
                "Indian",
                "Irish",
                "Italian",
                "Japanese",
                "Jewish",
                "Korean",
                "Mexican",
                "Native American / Indigenous",
                "Norwegian",
                "Persian / Iranian",
                "Polish",
                "Portuguese",
                "Russian",
                "Scottish",
                "Spanish",
                "Swedish",
                "Turkish",
                "Ukrainian",
                "Vietnamese",
                "Welsh",
                "International / blended",
                "Something else — I’ll describe it",
            ),
            deprecated_aliases=("heritage",),
        ),
        BabyTaxonomyField("notes"),
        BabyTaxonomyField(
            "discovery_style",
            current_choices=(
                "Classic favorites",
                "Balanced mix",
                "Unexpected finds",
                "Rare but wearable",
            ),
            legacy_choices=("Familiar favorites",),
            deprecated_aliases=("discovery",),
            prompt_key="discovery_direction",
        ),
        BabyTaxonomyField(
            "style",
            current_choices=(
                "Classic",
                "Modern",
                "Soft and romantic",
                "Strong and tailored",
                "Vintage revival",
                "Nature-inspired",
                "Globally familiar",
            ),
            legacy_choices=("Elegant",),
            deprecated_aliases=("name_style",),
            prompt_key="style_direction",
        ),
        BabyTaxonomyField(
            "timeless_vs_distinctive",
            current_choices=(
                "Strongly timeless",
                "Mostly timeless",
                "Balanced",
                "Mostly distinctive",
                "Strongly distinctive",
            ),
            deprecated_aliases=("distinctiveness",),
            prompt_key="distinctiveness_direction",
        ),
        BabyTaxonomyField(
            "familiarity_preference",
            current_choices=(
                "Very familiar and easy",
                "Recognizable but not overused",
                "A little less common",
                "Memorable and rarer",
            ),
            legacy_choices=("Very familiar",),
            deprecated_aliases=("familiarity",),
            prompt_key="familiarity_direction",
        ),
        BabyTaxonomyField(
            "sound",
            current_choices=("Soft", "Bright", "Strong", "Elegant", "Playful", "Calm", "Warm"),
            legacy_choices=("Clear", "Crisp"),
            deprecated_aliases=("sound_preference",),
            prompt_key="sound_direction",
        ),
        BabyTaxonomyField(
            "cultural_context",
            current_choices=(
                "Family heritage",
                "Nature",
                "Literature",
                "Saints & classics",
                "Music",
                "Places",
                "Meaning first",
                "Modern favorites",
            ),
            legacy_choices=("Global inspiration", "Honor names"),
            prompt_key="inspiration_direction",
        ),
        BabyTaxonomyField("partner_alignment"),
        BabyTaxonomyField("avoid", deprecated_aliases=("avoidances",)),
        BabyTaxonomyField("taste_strength_about_your_baby"),
        BabyTaxonomyField("taste_strength_name_style"),
        BabyTaxonomyField("taste_strength_fit_and_feeling"),
    ),
    legacy_migration_aliases=(
        ("baby_gender", "gender"),
        ("sex", "gender"),
        ("heritage", "cultural_heritage"),
        ("name_style", "style"),
        ("distinctiveness", "timeless_vs_distinctive"),
        ("familiarity", "familiarity_preference"),
        ("sound_preference", "sound"),
    ),
    migration_metadata_aliases=(
        ("baby_gender", "gender"),
        ("heritage", "cultural_heritage"),
        ("name_style", "style"),
    ),
)


# Compatibility exports keep the established import surface while making the
# taxonomy above the only declaration site for Baby choice labels.
BABY_GENDER_OPTIONS = BABY_TAXONOMY.current_choices("gender")
BABY_CULTURAL_HERITAGE_OPTIONS = BABY_TAXONOMY.current_choices("cultural_heritage")
BABY_DISCOVERY_STYLE_OPTIONS = BABY_TAXONOMY.current_choices("discovery_style")
BABY_STYLE_OPTIONS = BABY_TAXONOMY.current_choices("style")
BABY_DISTINCTIVENESS_OPTIONS = BABY_TAXONOMY.current_choices("timeless_vs_distinctive")
BABY_FAMILIARITY_OPTIONS = BABY_TAXONOMY.current_choices("familiarity_preference")
BABY_SOUND_OPTIONS = BABY_TAXONOMY.current_choices("sound")
BABY_INSPIRATION_OPTIONS = BABY_TAXONOMY.current_choices("cultural_context")


__all__ = [
    "BABY_CULTURAL_HERITAGE_OPTIONS",
    "BABY_DISCOVERY_STYLE_OPTIONS",
    "BABY_DISTINCTIVENESS_OPTIONS",
    "BABY_FAMILIARITY_OPTIONS",
    "BABY_GENDER_OPTIONS",
    "BABY_INSPIRATION_OPTIONS",
    "BABY_SOUND_OPTIONS",
    "BABY_STYLE_OPTIONS",
    "BABY_TAXONOMY",
    "BABY_TAXONOMY_VERSION",
    "BabyTaxonomy",
    "BabyTaxonomyField",
]
