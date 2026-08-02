"""Normalize user intake into shared naming briefs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from namengine.core.intake_limits import clip_intake_value, clip_text, intake_field_max_length
from namengine.core.schemas import NamingBrief, VerticalConfig


def _split_terms(value: str) -> list[str]:
    return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]


def build_brief(vertical: VerticalConfig, source: Mapping[str, Any]) -> NamingBrief:
    inputs: dict[str, Any] = {}

    for question in vertical.intake_questions:
        raw_value = source.get(question.id, "")
        value = clip_intake_value(question, raw_value)
        if value:
            inputs[question.id] = value

    if vertical.slug == "pet":
        _apply_pet_legacy_aliases(vertical, inputs, source)

    _apply_registered_intake_aliases(vertical, inputs, source)

    avoid_source = inputs.get("avoid", source.get("avoid", ""))
    avoid = _split_terms(str(avoid_source)) if avoid_source else []

    brief = NamingBrief(
        vertical=vertical.slug,
        inputs=inputs,
        avoid=avoid,
        notes=str(inputs.get("notes", "")),
    )
    # Preserve legacy inputs while registered verticals gain canonical intent.
    try:
        from namengine.core.intake import normalize_intake

        normalized = normalize_intake(vertical.slug, inputs, allow_partial=True)
    except (ImportError, ValueError):
        return brief
    if normalized.valid and normalized.canonical_intent is not None:
        brief.canonical_intent = normalized.canonical_intent.to_dict()
        brief.intake_metadata = normalized.version_metadata()
    return brief


def _question_limit_by_id(vertical: VerticalConfig, field_id: str) -> int | None:
    for question in vertical.intake_questions:
        if question.id == field_id:
            return intake_field_max_length(question)
    return None


def _clip_vertical_field(vertical: VerticalConfig, field_id: str, value: Any) -> Any:
    limit = _question_limit_by_id(vertical, field_id)
    return clip_text(value, limit) if limit is not None else clip_text(value, 180)


def _apply_pet_legacy_aliases(vertical: VerticalConfig, inputs: dict[str, Any], source: Mapping[str, Any]) -> None:
    aliases = {
        "species": "pet_type",
        "personality": "vibe",
    }
    for old_key, new_key in aliases.items():
        if new_key not in inputs and source.get(old_key):
            raw_value = source.get(old_key, "")
            inputs[new_key] = _clip_vertical_field(vertical, new_key, raw_value)
        if old_key not in inputs and inputs.get(new_key):
            inputs[old_key] = inputs[new_key]

    if "avoid" not in inputs and source.get("partner_alignment"):
        raw_value = source.get("partner_alignment", "")
        inputs["avoid"] = _clip_vertical_field(vertical, "avoid", raw_value)

    legacy_details = []
    for key in ("pet_life_stage", "notes"):
        value = source.get(key)
        if value:
            legacy_details.append(value.strip() if isinstance(value, str) else str(value))
    if legacy_details and not inputs.get("pet_details"):
        inputs["pet_details"] = _clip_vertical_field(vertical, "pet_details", "; ".join(legacy_details))


def _apply_registered_intake_aliases(
    vertical: VerticalConfig, inputs: dict[str, Any], source: Mapping[str, Any]
) -> None:
    """Map unambiguous registered aliases without changing canonical fields."""
    try:
        from namengine.core.intake import resolve_intake_schema

        schema = resolve_intake_schema(vertical.slug)
    except (ImportError, ValueError):
        return
    for definition in schema.fields:
        if definition.name in inputs or source.get(definition.name) not in (None, ""):
            continue
        supplied = [
            alias
            for alias in definition.aliases + definition.deprecated_aliases
            if source.get(alias) not in (None, "")
        ]
        if len(supplied) == 1:
            raw_value = source[supplied[0]]
            inputs[definition.name] = _clip_vertical_field(vertical, definition.name, raw_value)
