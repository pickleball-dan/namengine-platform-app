"""Current Baby questionnaire schema and canonical-intent adapter."""

from __future__ import annotations

from typing import Any

from namengine.core.canonical_intent import CANONICAL_INTENT_VERSION, CanonicalNamingIntent
from namengine.core.intake import (
    IntakeAdapter,
    IntakeFieldDefinition,
    IntakeMessage,
    IntakeSchema,
    register_intake_adapter,
    register_intake_schema,
)
from namengine.core.intake_migrations import IntakeMigration, register_intake_migration
from namengine.verticals.baby_taxonomy import (
    BABY_CULTURAL_HERITAGE_OPTIONS,
    BABY_DISTINCTIVENESS_OPTIONS,
    BABY_GENDER_OPTIONS,
    BABY_TAXONOMY,
)


BABY_INTAKE_VERSION = "baby-intake-v1"
BABY_LEGACY_INTAKE_VERSION = "baby-intake-v1-legacy"
BABY_NORMALIZER_VERSION = "baby-intake-normalizer-v1"
BABY_INTAKE_ADAPTER_VERSION = "baby-intake-adapter-v1"

# Historical fixtures and saved result links used additional labels before the
# current UI wording. Taxonomy v1 keeps those accepted values explicit.
_BABY_DISCOVERY_VALUES = BABY_TAXONOMY.accepted_choices("discovery_style")
_BABY_STYLE_VALUES = BABY_TAXONOMY.accepted_choices("style")
_BABY_FAMILIARITY_VALUES = BABY_TAXONOMY.accepted_choices("familiarity_preference")
_BABY_SOUND_VALUES = BABY_TAXONOMY.accepted_choices("sound")
_BABY_INSPIRATION_VALUES = BABY_TAXONOMY.accepted_choices("cultural_context")


def _text(
    name: str,
    *,
    required: bool = False,
    aliases: tuple[str, ...] = (),
    deprecated_aliases: tuple[str, ...] = (),
    choices: tuple[str, ...] = (),
    intent_path: str,
    sensitive: str = "none",
    max_length: int = 500,
) -> IntakeFieldDefinition:
    return IntakeFieldDefinition(
        name=name,
        data_type="string",
        required=required,
        aliases=aliases,
        deprecated_aliases=deprecated_aliases,
        allowed_values=choices,
        max_length=max_length,
        normalization="collapse",
        intent_path=intent_path,
        sensitive_classification=sensitive,
    )


BABY_INTAKE_SCHEMA = IntakeSchema(
    schema_id="namengine-baby-intake",
    schema_version=BABY_INTAKE_VERSION,
    vertical="baby",
    display_name="Baby Intake v1",
    description="The current production Baby questionnaire and Feelings Scale inputs.",
    fields=(
        _text("gender", required=True, deprecated_aliases=BABY_TAXONOMY.deprecated_aliases("gender"), choices=BABY_GENDER_OPTIONS, intent_path="gender_context"),
        _text("family_context", deprecated_aliases=BABY_TAXONOMY.deprecated_aliases("family_context"), intent_path="family_personal_context", sensitive="personal_context", max_length=1000),
        _text("cultural_heritage", deprecated_aliases=BABY_TAXONOMY.deprecated_aliases("cultural_heritage"), choices=BABY_CULTURAL_HERITAGE_OPTIONS, intent_path="cultural_contexts"),
        _text("notes", intent_path="notes", sensitive="personal_context", max_length=1500),
        _text("discovery_style", deprecated_aliases=BABY_TAXONOMY.deprecated_aliases("discovery_style"), choices=_BABY_DISCOVERY_VALUES, intent_path="discovery_preference"),
        _text("style", required=True, deprecated_aliases=BABY_TAXONOMY.deprecated_aliases("style"), choices=_BABY_STYLE_VALUES, intent_path="naming_styles"),
        _text("timeless_vs_distinctive", deprecated_aliases=BABY_TAXONOMY.deprecated_aliases("timeless_vs_distinctive"), choices=BABY_DISTINCTIVENESS_OPTIONS, intent_path="distinctiveness_preference"),
        _text("familiarity_preference", deprecated_aliases=BABY_TAXONOMY.deprecated_aliases("familiarity_preference"), choices=_BABY_FAMILIARITY_VALUES, intent_path="familiarity_preference"),
        _text("sound", required=True, deprecated_aliases=BABY_TAXONOMY.deprecated_aliases("sound"), choices=_BABY_SOUND_VALUES, intent_path="sound_qualities"),
        _text("cultural_context", choices=_BABY_INSPIRATION_VALUES, intent_path="cultural_contexts"),
        _text("partner_alignment", intent_path="extensions.partner_alignment", sensitive="personal_context", max_length=1000),
        _text("avoid", deprecated_aliases=BABY_TAXONOMY.deprecated_aliases("avoid"), intent_path="avoidances", sensitive="personal_context", max_length=1000),
        IntakeFieldDefinition(
            "taste_strength_about_your_baby",
            data_type="integer",
            minimum=0,
            maximum=100,
            intent_path="priority_weights.about_your_baby",
        ),
        IntakeFieldDefinition(
            "taste_strength_name_style",
            data_type="integer",
            minimum=0,
            maximum=100,
            intent_path="priority_weights.name_style",
        ),
        IntakeFieldDefinition(
            "taste_strength_fit_and_feeling",
            data_type="integer",
            minimum=0,
            maximum=100,
            intent_path="priority_weights.fit_and_feeling",
        ),
    ),
    unknown_field_policy="reject",
    normalizer_version=BABY_NORMALIZER_VERSION,
    migration_metadata={
        "legacy_source_version": BABY_LEGACY_INTAKE_VERSION,
        "deprecated_aliases_supported": True,
    },
)


def _build_baby_intent(values: dict[str, Any], schema: IntakeSchema) -> CanonicalNamingIntent:
    heritage = str(values.get("cultural_heritage") or "")
    inspiration = str(values.get("cultural_context") or "")
    cultural = tuple(
        item for item in (heritage, inspiration) if item and item.casefold() != "no preference"
    )
    sound = str(values.get("sound") or "")
    family = str(values.get("family_context") or "")
    partner = str(values.get("partner_alignment") or "")
    notes = str(values.get("notes") or "")
    combined_context = " ".join((family, partner, notes)).casefold()
    honor = ""
    if "honor" in combined_context or "family name" in combined_context:
        honor = family or partner or notes
    priority_values = {
        "about_your_baby": values.get("taste_strength_about_your_baby"),
        "name_style": values.get("taste_strength_name_style"),
        "fit_and_feeling": values.get("taste_strength_fit_and_feeling"),
    }
    supplied = {key: float(value) for key, value in priority_values.items() if value is not None}
    total = sum(supplied.values())
    if supplied:
        priority_weights = {
            key: round(value / total, 6) if total > 0 else 0.0
            for key, value in sorted(supplied.items())
        }
    else:
        priority_weights = {}
    avoidances = tuple(
        item.strip()
        for item in str(values.get("avoid") or "").replace(";", ",").split(",")
        if item.strip()
    )
    distinctiveness = str(values.get("timeless_vs_distinctive") or "")
    geographic = ()
    if any(term in combined_context for term in ("language", "united states", " us ", "bilingual")):
        geographic = tuple(item for item in (family, notes) if item)
    return CanonicalNamingIntent(
        vertical="baby",
        naming_target="baby name",
        gender_context=str(values.get("gender") or ""),
        cultural_contexts=cultural,
        naming_styles=tuple(item for item in (str(values.get("style") or ""),) if item),
        familiarity_preference=str(values.get("familiarity_preference") or ""),
        distinctiveness_preference=distinctiveness,
        sound_qualities=tuple(item for item in (sound,) if item),
        emotional_qualities=tuple(item for item in (sound,) if item in {"Warm", "Playful", "Calm", "Bright", "Elegant"}),
        strength_softness=sound if sound in {"Soft", "Strong"} else "",
        temporal_preference=distinctiveness if "timeless" in distinctiveness.casefold() else "",
        discovery_preference=str(values.get("discovery_style") or ""),
        family_personal_context=family,
        honor_name_influence=honor,
        usage_contexts=("family", "childhood", "adulthood"),
        professional_usability="important" if "professional" in combined_context else "",
        geographic_language_contexts=geographic,
        avoidances=avoidances,
        notes=notes,
        priority_weights=priority_weights,
        source_intake_version=schema.schema_version,
        normalization_version=schema.normalizer_version,
        extensions={"partner_alignment": partner} if partner else {},
    )


def _validate_baby_values(
    values: dict[str, Any], schema: IntakeSchema
) -> tuple[list[IntakeMessage], list[IntakeMessage]]:
    errors: list[IntakeMessage] = []
    warnings: list[IntakeMessage] = []
    notes = str(values.get("notes") or "").casefold()
    gender = str(values.get("gender") or "").casefold()
    if gender == "gender-neutral" and any(term in notes for term in ("boy only", "girl only")):
        errors.append(
            IntakeMessage(
                "gender",
                "contradictory_gender_context",
                "Gender direction conflicts with another supplied constraint",
            )
        )
    if (
        values.get("cultural_heritage") == "No preference"
        and values.get("cultural_context") == "Family heritage"
    ):
        warnings.append(
            IntakeMessage(
                "cultural_heritage",
                "heritage_detail_recommended",
                "Family heritage was selected without a specific heritage preference",
            )
        )
    return errors, warnings


def _migrate_legacy_baby(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    migrated = dict(payload)
    mappings = BABY_TAXONOMY.legacy_migration_mapping()
    warnings: list[str] = []
    for old, new in mappings.items():
        if old not in migrated:
            continue
        if new in migrated and migrated[new] != migrated[old]:
            continue
        migrated.setdefault(new, migrated[old])
        migrated.pop(old, None)
        warnings.append(f"{old} migrated to {new}")
    return migrated, warnings


BABY_INTAKE_ADAPTER = IntakeAdapter(
    vertical_slug="baby",
    version=BABY_INTAKE_ADAPTER_VERSION,
    canonical_intent_version=CANONICAL_INTENT_VERSION,
    build_intent=_build_baby_intent,
    validate_values=_validate_baby_values,
)

register_intake_adapter(BABY_INTAKE_ADAPTER, platform_default=True)
register_intake_schema(BABY_INTAKE_SCHEMA, make_default=True, platform_default=True)
register_intake_migration(
    IntakeMigration(
        vertical="baby",
        source_version=BABY_LEGACY_INTAKE_VERSION,
        destination_version=BABY_INTAKE_VERSION,
        migrate=_migrate_legacy_baby,
        deprecated_field_mapping=BABY_TAXONOMY.migration_metadata_mapping(),
    )
)
