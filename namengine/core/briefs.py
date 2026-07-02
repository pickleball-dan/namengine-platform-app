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

    avoid_source = inputs.get("avoid", source.get("avoid", ""))
    avoid = _split_terms(str(avoid_source)) if avoid_source else []

    return NamingBrief(
        vertical=vertical.slug,
        inputs=inputs,
        avoid=avoid,
        notes=str(inputs.get("notes", "")),
    )


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
