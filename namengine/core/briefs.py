"""Normalize user intake into shared naming briefs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from namengine.core.schemas import NamingBrief, VerticalConfig


def _split_terms(value: str) -> list[str]:
    return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]


def build_brief(vertical: VerticalConfig, source: Mapping[str, Any]) -> NamingBrief:
    inputs: dict[str, Any] = {}

    for question in vertical.intake_questions:
        raw_value = source.get(question.id, "")
        value = raw_value.strip() if isinstance(raw_value, str) else raw_value
        if value:
            inputs[question.id] = value

    if vertical.slug == "pet":
        _apply_pet_legacy_aliases(inputs, source)

    _apply_registered_intake_aliases(vertical.slug, inputs, source)

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


def _apply_pet_legacy_aliases(inputs: dict[str, Any], source: Mapping[str, Any]) -> None:
    aliases = {
        "species": "pet_type",
        "personality": "vibe",
    }
    for old_key, new_key in aliases.items():
        if new_key not in inputs and source.get(old_key):
            raw_value = source.get(old_key, "")
            inputs[new_key] = raw_value.strip() if isinstance(raw_value, str) else raw_value
        if old_key not in inputs and inputs.get(new_key):
            inputs[old_key] = inputs[new_key]


def _apply_registered_intake_aliases(
    vertical_slug: str, inputs: dict[str, Any], source: Mapping[str, Any]
) -> None:
    """Map unambiguous registered aliases without changing canonical fields."""
    try:
        from namengine.core.intake import resolve_intake_schema

        schema = resolve_intake_schema(vertical_slug)
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
            inputs[definition.name] = raw_value.strip() if isinstance(raw_value, str) else raw_value
