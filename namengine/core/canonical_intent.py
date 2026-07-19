"""Stable cross-vertical naming intent produced from versioned intake."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any


CANONICAL_INTENT_VERSION = "canonical-naming-intent-v1"
MAX_INTENT_TEXT = 1000
MAX_INTENT_ITEMS = 100
_RESERVED_EXTENSION_KEYS = frozenset(
    {"__proto__", "constructor", "prototype", "metadata", "canonical_intent", "raw_intake"}
)


@dataclass(frozen=True, slots=True)
class CanonicalNamingIntent:
    vertical: str
    naming_target: str
    gender_context: str = ""
    cultural_contexts: tuple[str, ...] = ()
    naming_styles: tuple[str, ...] = ()
    familiarity_preference: str = ""
    distinctiveness_preference: str = ""
    sound_qualities: tuple[str, ...] = ()
    emotional_qualities: tuple[str, ...] = ()
    strength_softness: str = ""
    temporal_preference: str = ""
    discovery_preference: str = ""
    family_personal_context: str = ""
    honor_name_influence: str = ""
    usage_contexts: tuple[str, ...] = ()
    professional_usability: str = ""
    geographic_language_contexts: tuple[str, ...] = ()
    avoidances: tuple[str, ...] = ()
    notes: str = ""
    priority_weights: dict[str, float] = field(default_factory=dict)
    source_intake_version: str = ""
    normalization_version: str = ""
    intent_version: str = CANONICAL_INTENT_VERSION
    extensions: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.vertical or self.vertical != self.vertical.strip().lower():
            raise ValueError("Canonical intent requires a lowercase vertical")
        if self.intent_version != CANONICAL_INTENT_VERSION:
            raise ValueError("Unsupported canonical intent version")
        for key, value in self.priority_weights.items():
            if not key or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Canonical priority weights must be finite")
            if not 0 <= float(value) <= 1:
                raise ValueError("Canonical priority weights must be bounded")
        _validate_extensions(self.extensions)

    def to_dict(self) -> dict[str, Any]:
        return _bounded_json(asdict(self))

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _validate_extensions(value: dict[str, Any], depth: int = 0) -> None:
    if depth > 8 or len(value) > MAX_INTENT_ITEMS:
        raise ValueError("Canonical extensions exceed bounds")
    for key, item in value.items():
        normalized = str(key).strip().lower()
        if (
            not normalized
            or len(normalized) > 100
            or normalized in _RESERVED_EXTENSION_KEYS
            or normalized.startswith("_")
        ):
            raise ValueError("Canonical extension key is reserved or invalid")
        if isinstance(item, dict):
            _validate_extensions(item, depth + 1)
        elif isinstance(item, (list, tuple)):
            if len(item) > MAX_INTENT_ITEMS:
                raise ValueError("Canonical extension collection exceeds bounds")
            for child in item:
                _validate_extension_value(child, depth + 1)
        else:
            _validate_extension_value(item, depth + 1)


def _validate_extension_value(value: Any, depth: int) -> None:
    if isinstance(value, dict):
        _validate_extensions(value, depth)
    elif isinstance(value, str) and len(value) > MAX_INTENT_TEXT:
        raise ValueError("Canonical extension text exceeds bounds")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Canonical extensions require finite numbers")
    elif value is not None and not isinstance(value, (str, bool, int, float)):
        raise ValueError("Canonical extensions must be JSON-safe")


def _bounded_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key)[:100]: _bounded_json(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))[:MAX_INTENT_ITEMS]
        }
    if isinstance(value, (list, tuple)):
        return [_bounded_json(item) for item in value[:MAX_INTENT_ITEMS]]
    if isinstance(value, str):
        return value[:MAX_INTENT_TEXT]
    if isinstance(value, float):
        return round(value, 6) if math.isfinite(value) else None
    if value is None or isinstance(value, (bool, int)):
        return value
    return str(value)[:MAX_INTENT_TEXT]
