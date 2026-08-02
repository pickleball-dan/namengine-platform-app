"""Server-side intake length limits shared by views and brief normalization."""

from __future__ import annotations

from typing import Any


DEFAULT_TEXT_INPUT_MAX_LENGTH = 180
DEFAULT_TEXTAREA_MAX_LENGTH = 750
OTHER_CHOICE_MAX_LENGTH = 120
REFINEMENT_INSTRUCTION_MAX_LENGTH = 200
INTAKE_FIELD_MAX_LENGTHS = {
    "avoid": 500,
    "business_description": 1000,
    "category": 140,
    "family_context": 1000,
    "industry": 140,
    "notes": 1000,
    "partner_alignment": 750,
    "pet_breed": 140,
    "pet_color": 120,
    "pet_details": 750,
    "product_description": 1000,
}


def intake_field_max_length(question: Any) -> int:
    """Return the canonical character limit for an intake question."""
    if isinstance(question, dict):
        field_id = str(question.get("id", ""))
        kind = str(question.get("kind", ""))
    else:
        field_id = getattr(question, "id", "")
        kind = getattr(question, "kind", "")
    if field_id in INTAKE_FIELD_MAX_LENGTHS:
        return INTAKE_FIELD_MAX_LENGTHS[field_id]
    if kind == "textarea":
        return DEFAULT_TEXTAREA_MAX_LENGTH
    return DEFAULT_TEXT_INPUT_MAX_LENGTH


def clip_text(value: Any, max_length: int) -> Any:
    """Strip string values and cap them at the supplied character limit."""
    if not isinstance(value, str):
        return value
    return value.strip()[:max_length]


def clip_intake_value(question: Any, value: Any) -> Any:
    """Apply the canonical backend limit for a vertical intake question."""
    return clip_text(value, intake_field_max_length(question))
