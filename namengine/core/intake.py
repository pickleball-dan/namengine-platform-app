"""Versioned intake schemas, validation, normalization, adapters, and comparison."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from threading import RLock
from typing import Any, Literal

from namengine.core.canonical_intent import CANONICAL_INTENT_VERSION, CanonicalNamingIntent
from namengine.core.intake_migrations import IntakeMigrationError, migrate_intake


MAX_INTAKE_TEXT = 2000
MAX_INTAKE_ITEMS = 100
MAX_MESSAGE_TEXT = 500
UNKNOWN_FIELD_POLICIES = frozenset({"reject", "warn", "allow"})
DATA_TYPES = frozenset({"string", "integer", "number", "boolean", "string_list", "object"})
_RESERVED_KEYS = frozenset(
    {
        "__proto__",
        "constructor",
        "prototype",
        "metadata",
        "canonical_intent",
        "intake_metadata",
        "raw_intake",
    }
)


class IntakeSchemaError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class IntakeFieldDefinition:
    name: str
    data_type: str = "string"
    required: bool = False
    has_default: bool = False
    default: Any = None
    aliases: tuple[str, ...] = ()
    deprecated_aliases: tuple[str, ...] = ()
    allowed_values: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    max_length: int = MAX_INTAKE_TEXT
    max_items: int = MAX_INTAKE_ITEMS
    normalization: str = "trim"
    intent_path: str = "extensions"
    sensitive_classification: str = "none"
    applicable_when: dict[str, tuple[Any, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _canonical_field_name(self.name) or self.name in _RESERVED_KEYS:
            raise ValueError("Intake field name is invalid or reserved")
        if self.data_type not in DATA_TYPES:
            raise ValueError(f"Unsupported intake data type: {self.data_type}")
        all_aliases = self.aliases + self.deprecated_aliases
        if len(set(all_aliases)) != len(all_aliases) or self.name in all_aliases:
            raise ValueError("Intake field aliases must be unique")
        if any(not _canonical_field_name(alias) or alias in _RESERVED_KEYS for alias in all_aliases):
            raise ValueError("Intake field alias is invalid or reserved")
        if self.minimum is not None and not math.isfinite(float(self.minimum)):
            raise ValueError("Intake minimum must be finite")
        if self.maximum is not None and not math.isfinite(float(self.maximum)):
            raise ValueError("Intake maximum must be finite")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("Intake range is inverted")
        if self.max_length < 0 or self.max_items < 0:
            raise ValueError("Intake bounds must be non-negative")
        _json_copy(self.default)


@dataclass(frozen=True, slots=True)
class IntakeSchema:
    schema_id: str
    schema_version: str
    vertical: str
    display_name: str
    description: str
    fields: tuple[IntakeFieldDefinition, ...]
    unknown_field_policy: str
    normalizer_version: str
    migration_metadata: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.schema_id.strip() or not self.schema_version.strip():
            raise ValueError("Intake schema identifiers must be non-empty")
        if not _canonical_slug(self.vertical):
            raise ValueError("Intake schema vertical must be a canonical slug")
        if not self.display_name.strip() or not self.normalizer_version.strip():
            raise ValueError("Intake schemas require display and normalizer versions")
        if self.unknown_field_policy not in UNKNOWN_FIELD_POLICIES:
            raise ValueError("Unknown-field policy is invalid")
        names = [item.name for item in self.fields]
        aliases = [alias for item in self.fields for alias in item.aliases + item.deprecated_aliases]
        if not self.fields or len(names) != len(set(names)):
            raise ValueError("Intake schema field names must be non-empty and unique")
        if set(names) & set(aliases) or len(aliases) != len(set(aliases)):
            raise ValueError("Intake aliases collide with schema fields")
        _json_copy(self.migration_metadata)

    def to_dict(self) -> dict[str, Any]:
        return _json_copy(asdict(self))


@dataclass(frozen=True, slots=True)
class IntakeMessage:
    field_path: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IntakeValidationResult:
    valid: bool
    vertical: str
    schema_version: str
    errors: tuple[IntakeMessage, ...] = ()
    warnings: tuple[IntakeMessage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "vertical": self.vertical,
            "schema_version": self.schema_version,
            "errors": [item.to_dict() for item in self.errors],
            "warnings": [item.to_dict() for item in self.warnings],
        }


@dataclass(frozen=True, slots=True)
class IntakeAdapter:
    vertical_slug: str
    version: str
    canonical_intent_version: str
    build_intent: Callable[[dict[str, Any], IntakeSchema], CanonicalNamingIntent]
    validate_values: Callable[[dict[str, Any], IntakeSchema], tuple[list[IntakeMessage], list[IntakeMessage]]] | None = None

    def __post_init__(self) -> None:
        if not _canonical_slug(self.vertical_slug) or not self.version.strip():
            raise ValueError("Intake adapter identity is invalid")
        if self.canonical_intent_version != CANONICAL_INTENT_VERSION:
            raise ValueError("Intake adapter canonical intent version is unsupported")


@dataclass(frozen=True, slots=True)
class IntakeNormalizationResult:
    valid: bool
    vertical: str
    intake_version: str
    normalizer_version: str
    adapter_version: str
    canonical_intent_version: str
    canonical_intent: CanonicalNamingIntent | None
    validation: IntakeValidationResult
    applied_defaults: tuple[str, ...] = ()
    applied_aliases: tuple[dict[str, str], ...] = ()
    deprecation_warnings: tuple[str, ...] = ()
    validation_warnings: tuple[IntakeMessage, ...] = ()
    migration_source_version: str = ""
    migration_destination_version: str = ""
    migration_history: tuple[str, ...] = ()
    migration_warnings: tuple[str, ...] = ()

    def version_metadata(self) -> dict[str, str]:
        metadata = {
            "intake_schema_version": self.intake_version,
            "normalizer_version": self.normalizer_version,
            "intake_adapter_version": self.adapter_version,
            "canonical_intent_version": self.canonical_intent_version,
        }
        if self.migration_source_version:
            metadata["migration_source_version"] = self.migration_source_version
            metadata["migration_destination_version"] = self.migration_destination_version
        return metadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "vertical": self.vertical,
            "intake_version": self.intake_version,
            "normalizer_version": self.normalizer_version,
            "adapter_version": self.adapter_version,
            "canonical_intent_version": self.canonical_intent_version,
            "canonical_intent": self.canonical_intent.to_dict() if self.canonical_intent else None,
            "validation": self.validation.to_dict(),
            "applied_defaults": list(self.applied_defaults),
            "applied_aliases": list(self.applied_aliases),
            "deprecation_warnings": list(self.deprecation_warnings),
            "validation_warnings": [item.to_dict() for item in self.validation_warnings],
            "migration_source_version": self.migration_source_version,
            "migration_destination_version": self.migration_destination_version,
            "migration_history": list(self.migration_history),
            "migration_warnings": list(self.migration_warnings),
        }

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True, slots=True)
class IntakeComparison:
    added_fields: tuple[str, ...]
    removed_fields: tuple[str, ...]
    changed_fields: tuple[str, ...]
    changed_priority_weights: tuple[str, ...]
    migration_warnings: tuple[str, ...]
    semantic_summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_fields": list(self.added_fields),
            "removed_fields": list(self.removed_fields),
            "changed_fields": list(self.changed_fields),
            "changed_priority_weights": list(self.changed_priority_weights),
            "migration_warnings": list(self.migration_warnings),
            "semantic_summary": self.semantic_summary,
        }

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


_SCHEMAS: dict[tuple[str, str], IntakeSchema] = {}
_DEFAULTS: dict[str, str] = {}
_PLATFORM_SCHEMAS: dict[tuple[str, str], IntakeSchema] = {}
_PLATFORM_DEFAULTS: dict[str, str] = {}
_ADAPTERS: dict[str, IntakeAdapter] = {}
_PLATFORM_ADAPTERS: dict[str, IntakeAdapter] = {}
_LOCK = RLock()


def register_intake_schema(
    schema: IntakeSchema,
    *,
    make_default: bool = False,
    platform_default: bool = False,
) -> None:
    key = (schema.vertical, schema.schema_version)
    with _LOCK:
        existing = _SCHEMAS.get(key)
        if existing is not None and existing != schema:
            raise ValueError(f"An intake schema is already registered for {key}")
        _SCHEMAS[key] = schema
        if make_default or schema.vertical not in _DEFAULTS:
            _DEFAULTS[schema.vertical] = schema.schema_version
        if platform_default:
            _PLATFORM_SCHEMAS[key] = schema
            _PLATFORM_DEFAULTS[schema.vertical] = schema.schema_version


def unregister_intake_schema(vertical: str, version: str) -> None:
    slug = vertical.strip().lower()
    key = (slug, version.strip())
    with _LOCK:
        if key in _PLATFORM_SCHEMAS:
            _SCHEMAS[key] = _PLATFORM_SCHEMAS[key]
        else:
            _SCHEMAS.pop(key, None)
        if _DEFAULTS.get(slug) == key[1]:
            platform_version = _PLATFORM_DEFAULTS.get(slug)
            if platform_version:
                _DEFAULTS[slug] = platform_version
            else:
                remaining = sorted(item[1] for item in _SCHEMAS if item[0] == slug)
                if remaining:
                    _DEFAULTS[slug] = remaining[0]
                else:
                    _DEFAULTS.pop(slug, None)


def set_default_intake_version(vertical: str, version: str) -> None:
    slug = vertical.strip().lower()
    with _LOCK:
        if (slug, version) not in _SCHEMAS:
            raise IntakeSchemaError(f"Unsupported intake schema: {slug}/{version}")
        _DEFAULTS[slug] = version


def resolve_intake_schema(vertical: str, version: str | None = None) -> IntakeSchema:
    _load_builtin_adapters()
    slug = vertical.strip().lower()
    if not _canonical_slug(slug):
        raise IntakeSchemaError("Invalid vertical slug")
    with _LOCK:
        selected = version.strip() if version else _DEFAULTS.get(slug, "")
        schema = _SCHEMAS.get((slug, selected))
    if schema is None:
        raise IntakeSchemaError(f"Unsupported intake schema: {slug}/{selected or 'default'}")
    if not schema.enabled:
        raise IntakeSchemaError(f"Intake schema is disabled: {slug}/{selected}")
    return schema


def list_intake_schemas(vertical: str | None = None) -> tuple[dict[str, Any], ...]:
    _load_builtin_adapters()
    with _LOCK:
        schemas = sorted(_SCHEMAS.values(), key=lambda item: (item.vertical, item.schema_version))
        defaults = dict(_DEFAULTS)
    return tuple(
        {
            "schema_id": schema.schema_id,
            "schema_version": schema.schema_version,
            "vertical": schema.vertical,
            "display_name": schema.display_name,
            "normalizer_version": schema.normalizer_version,
            "enabled": schema.enabled,
            "default": defaults.get(schema.vertical) == schema.schema_version,
        }
        for schema in schemas
        if vertical is None or schema.vertical == vertical
    )


def register_intake_adapter(adapter: IntakeAdapter, *, platform_default: bool = False) -> None:
    with _LOCK:
        existing = _ADAPTERS.get(adapter.vertical_slug)
        if existing is not None and existing != adapter:
            raise ValueError(f"An intake adapter is already registered for {adapter.vertical_slug}")
        _ADAPTERS[adapter.vertical_slug] = adapter
        if platform_default:
            _PLATFORM_ADAPTERS[adapter.vertical_slug] = adapter


def unregister_intake_adapter(vertical: str) -> None:
    slug = vertical.strip().lower()
    with _LOCK:
        platform = _PLATFORM_ADAPTERS.get(slug)
        if platform is None:
            _ADAPTERS.pop(slug, None)
        else:
            _ADAPTERS[slug] = platform


def intake_adapter_for(vertical: str) -> IntakeAdapter | None:
    _load_builtin_adapters()
    with _LOCK:
        return _ADAPTERS.get(vertical.strip().lower())


def validate_intake(
    vertical: str,
    payload: Mapping[str, Any] | Any,
    *,
    intake_version: str | None = None,
    allow_partial: bool = False,
) -> IntakeValidationResult:
    try:
        schema = resolve_intake_schema(vertical, intake_version)
    except IntakeSchemaError as exc:
        message = IntakeMessage("$", "unsupported_schema", str(exc)[:MAX_MESSAGE_TEXT])
        return IntakeValidationResult(False, vertical.strip().lower(), intake_version or "", (message,))
    values, errors, warnings, _defaults, _aliases, _deprecated = _prepare_payload(
        schema, payload, allow_partial=allow_partial
    )
    adapter = intake_adapter_for(schema.vertical)
    if adapter and adapter.validate_values and not errors:
        adapter_errors, adapter_warnings = adapter.validate_values(values, schema)
        errors.extend(adapter_errors)
        warnings.extend(adapter_warnings)
    errors = _bounded_messages(errors)
    warnings = _bounded_messages(warnings)
    return IntakeValidationResult(
        not errors,
        schema.vertical,
        schema.schema_version,
        tuple(errors),
        tuple(warnings),
    )


def normalize_intake(
    vertical: str,
    payload: Mapping[str, Any] | Any,
    *,
    intake_version: str | None = None,
    target_version: str | None = None,
    allow_partial: bool = False,
) -> IntakeNormalizationResult:
    _load_builtin_adapters()
    slug = vertical.strip().lower()
    migration_source = ""
    migration_destination = ""
    migration_history: tuple[str, ...] = ()
    migration_warnings: tuple[str, ...] = ()
    migrated_payload = payload
    selected_source = intake_version
    try:
        target_schema = resolve_intake_schema(slug, target_version)
        if selected_source and selected_source != target_schema.schema_version:
            if not isinstance(payload, Mapping):
                raise IntakeMigrationError("Migration payload must be an object")
            migration = migrate_intake(
                slug,
                dict(payload),
                selected_source,
                target_schema.schema_version,
            )
            migrated_payload = migration.payload
            migration_source = migration.source_version
            migration_destination = migration.destination_version
            migration_history = migration.history
            migration_warnings = migration.warnings
        elif selected_source:
            target_schema = resolve_intake_schema(slug, selected_source)
    except (IntakeSchemaError, IntakeMigrationError) as exc:
        version = target_version or selected_source or ""
        validation = IntakeValidationResult(
            False,
            slug,
            version,
            (IntakeMessage("$", "unsupported_schema_or_migration", str(exc)[:MAX_MESSAGE_TEXT]),),
        )
        return IntakeNormalizationResult(
            False, slug, version, "", "", CANONICAL_INTENT_VERSION, None, validation
        )

    values, errors, warnings, defaults, aliases, deprecated = _prepare_payload(
        target_schema, migrated_payload, allow_partial=allow_partial
    )
    adapter = intake_adapter_for(slug)
    if adapter is None:
        errors.append(IntakeMessage("$", "missing_adapter", "No intake adapter is registered"))
    elif adapter.validate_values and not errors:
        adapter_errors, adapter_warnings = adapter.validate_values(values, target_schema)
        errors.extend(adapter_errors)
        warnings.extend(adapter_warnings)
    errors = _bounded_messages(errors)
    warnings = _bounded_messages(warnings)
    validation = IntakeValidationResult(
        not errors,
        slug,
        target_schema.schema_version,
        tuple(errors),
        tuple(warnings),
    )
    intent = adapter.build_intent(values, target_schema) if adapter and not errors else None
    return IntakeNormalizationResult(
        valid=not errors,
        vertical=slug,
        intake_version=target_schema.schema_version,
        normalizer_version=target_schema.normalizer_version,
        adapter_version=adapter.version if adapter else "",
        canonical_intent_version=adapter.canonical_intent_version if adapter else CANONICAL_INTENT_VERSION,
        canonical_intent=intent,
        validation=validation,
        applied_defaults=tuple(sorted(defaults)),
        applied_aliases=tuple(sorted(aliases, key=lambda item: (item["alias"], item["field"]))),
        deprecation_warnings=tuple(sorted(deprecated)),
        validation_warnings=tuple(warnings),
        migration_source_version=migration_source,
        migration_destination_version=migration_destination,
        migration_history=migration_history,
        migration_warnings=migration_warnings,
    )


def compare_normalized_intakes(
    left: IntakeNormalizationResult, right: IntakeNormalizationResult
) -> IntakeComparison:
    left_data = left.canonical_intent.to_dict() if left.canonical_intent else {}
    right_data = right.canonical_intent.to_dict() if right.canonical_intent else {}
    left_weights = dict(left_data.pop("priority_weights", {}) or {})
    right_weights = dict(right_data.pop("priority_weights", {}) or {})
    left_flat = _flatten(left_data)
    right_flat = _flatten(right_data)
    added = tuple(sorted(set(right_flat) - set(left_flat)))
    removed = tuple(sorted(set(left_flat) - set(right_flat)))
    changed = tuple(
        sorted(key for key in set(left_flat) & set(right_flat) if left_flat[key] != right_flat[key])
    )
    changed_weights = tuple(
        sorted(
            key
            for key in set(left_weights) | set(right_weights)
            if left_weights.get(key) != right_weights.get(key)
        )
    )
    migration_warnings = tuple(
        sorted(set(left.migration_warnings) | set(right.migration_warnings))
    )
    summary = (
        f"{len(added)} added, {len(removed)} removed, {len(changed)} changed canonical fields; "
        f"{len(changed_weights)} priority weights changed."
    )
    return IntakeComparison(added, removed, changed, changed_weights, migration_warnings, summary)


def version_metadata_for_brief(brief: Any) -> dict[str, str]:
    metadata = getattr(brief, "intake_metadata", {})
    if not isinstance(metadata, dict):
        return {}
    allowed = {
        "intake_schema_version",
        "normalizer_version",
        "intake_adapter_version",
        "migration_source_version",
        "migration_destination_version",
        "canonical_intent_version",
    }
    return {
        key: str(value)[:200]
        for key, value in metadata.items()
        if key in allowed and value not in (None, "")
    }


def _prepare_payload(
    schema: IntakeSchema,
    payload: Mapping[str, Any] | Any,
    *,
    allow_partial: bool,
) -> tuple[
    dict[str, Any],
    list[IntakeMessage],
    list[IntakeMessage],
    list[str],
    list[dict[str, str]],
    list[str],
]:
    errors: list[IntakeMessage] = []
    warnings: list[IntakeMessage] = []
    defaults: list[str] = []
    aliases: list[dict[str, str]] = []
    deprecated: list[str] = []
    if not isinstance(payload, Mapping):
        return {}, [IntakeMessage("$", "invalid_type", "Intake must be an object")], [], [], [], []
    try:
        _validate_json_value(dict(payload))
    except ValueError as exc:
        return {}, [IntakeMessage("$", "invalid_json", str(exc)[:MAX_MESSAGE_TEXT])], [], [], [], []
    source = dict(payload)
    field_by_key: dict[str, IntakeFieldDefinition] = {}
    for definition in schema.fields:
        field_by_key[definition.name] = definition
        for alias in definition.aliases + definition.deprecated_aliases:
            field_by_key[alias] = definition
    for key in source:
        if not isinstance(key, str) or key in _RESERVED_KEYS or key.startswith("_"):
            errors.append(IntakeMessage("$", "reserved_field", "Intake contains a reserved field"))
        elif key not in field_by_key:
            message = IntakeMessage(key[:100], "unknown_field", "Field is not defined by this intake schema")
            if schema.unknown_field_policy == "reject":
                errors.append(message)
            elif schema.unknown_field_policy == "warn":
                warnings.append(message)

    values: dict[str, Any] = {}
    for definition in schema.fields:
        supplied = [key for key in (definition.name,) + definition.aliases + definition.deprecated_aliases if key in source]
        if len(supplied) > 1:
            coerced = []
            for key in supplied:
                value, error = _coerce_field(definition, source[key])
                if error:
                    errors.append(IntakeMessage(definition.name, error[0], error[1]))
                else:
                    coerced.append(value)
            if coerced and any(item != coerced[0] for item in coerced[1:]):
                errors.append(
                    IntakeMessage(
                        definition.name,
                        "conflicting_aliases",
                        "Canonical field and alias contain conflicting values",
                    )
                )
                continue
        if supplied:
            selected = definition.name if definition.name in supplied else supplied[0]
            value, error = _coerce_field(definition, source[selected])
            if error:
                errors.append(IntakeMessage(definition.name, error[0], error[1]))
                continue
            values[definition.name] = value
            if selected != definition.name:
                aliases.append({"alias": selected, "field": definition.name})
                if selected in definition.deprecated_aliases:
                    deprecated.append(f"{selected} is deprecated; use {definition.name}")
            if definition.applicable_when and not _is_applicable(definition, source, values):
                warnings.append(
                    IntakeMessage(
                        definition.name,
                        "field_not_applicable",
                        "Field is not applicable for the selected intake context",
                    )
                )
        elif definition.has_default:
            values[definition.name] = _json_copy(definition.default)
            defaults.append(definition.name)
        elif definition.required and not allow_partial:
            errors.append(
                IntakeMessage(definition.name, "required", "Required intake field is missing")
            )
    return values, errors, warnings, defaults, aliases, deprecated


def _bounded_messages(messages: list[IntakeMessage]) -> list[IntakeMessage]:
    return [
        IntakeMessage(
            str(item.field_path)[:100],
            str(item.code)[:100],
            str(item.message)[:MAX_MESSAGE_TEXT],
        )
        for item in messages[:MAX_INTAKE_ITEMS]
    ]


def _coerce_field(
    definition: IntakeFieldDefinition, raw: Any
) -> tuple[Any, tuple[str, str] | None]:
    try:
        if definition.data_type == "string":
            if not isinstance(raw, str):
                return None, ("invalid_type", "Field must be text")
            value: Any = " ".join(raw.strip().split()) if definition.normalization == "collapse" else raw.strip()
            if len(value) > definition.max_length:
                return None, ("string_too_long", "Field exceeds its maximum length")
            if definition.allowed_values:
                matched = _match_enum(value, definition.allowed_values)
                if matched is None:
                    return None, ("invalid_enum", "Field contains an unsupported option")
                value = matched
            return value, None
        if definition.data_type in {"integer", "number"}:
            if isinstance(raw, bool):
                return None, ("invalid_number", "Field must be numeric")
            if isinstance(raw, str):
                text = raw.strip()
                pattern = r"[-+]?\d+" if definition.data_type == "integer" else r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
                if not re.fullmatch(pattern, text):
                    return None, ("invalid_number", "Field must be numeric")
                value = int(text) if definition.data_type == "integer" else float(text)
            elif isinstance(raw, (int, float)):
                value = int(raw) if definition.data_type == "integer" and float(raw).is_integer() else raw
                if definition.data_type == "integer" and not isinstance(value, int):
                    return None, ("invalid_number", "Field must be an integer")
            else:
                return None, ("invalid_number", "Field must be numeric")
            if not math.isfinite(float(value)):
                return None, ("non_finite", "Field must be a finite number")
            if definition.minimum is not None and value < definition.minimum:
                return None, ("below_minimum", "Field is below its minimum")
            if definition.maximum is not None and value > definition.maximum:
                return None, ("above_maximum", "Field exceeds its maximum")
            return value, None
        if definition.data_type == "boolean":
            if isinstance(raw, bool):
                return raw, None
            if isinstance(raw, int) and raw in {0, 1}:
                return bool(raw), None
            if isinstance(raw, str) and raw.strip().lower() in {"true", "false", "1", "0"}:
                return raw.strip().lower() in {"true", "1"}, None
            return None, ("invalid_boolean", "Field must be an unambiguous boolean")
        if definition.data_type == "string_list":
            if not isinstance(raw, (list, tuple)):
                return None, ("invalid_type", "Field must be a list of text values")
            if len(raw) > definition.max_items:
                return None, ("collection_too_large", "Field contains too many items")
            if any(not isinstance(item, str) for item in raw):
                return None, ("invalid_collection_item", "Field list items must be text")
            values = tuple(item.strip() for item in raw)
            if any(len(item) > definition.max_length for item in values):
                return None, ("string_too_long", "Field contains oversized text")
            return values, None
        if definition.data_type == "object":
            if not isinstance(raw, Mapping):
                return None, ("invalid_type", "Field must be an object")
            if len(raw) > definition.max_items:
                return None, ("collection_too_large", "Field contains too many entries")
            _validate_json_value(dict(raw))
            return _json_copy(dict(raw)), None
    except (TypeError, ValueError):
        return None, ("malformed_value", "Field value is malformed")
    return None, ("invalid_type", "Field type is unsupported")


def _match_enum(value: str, choices: tuple[str, ...]) -> str | None:
    normalized = " ".join(value.casefold().split())
    for choice in choices:
        if " ".join(choice.casefold().split()) == normalized:
            return choice
    return None


def _is_applicable(
    definition: IntakeFieldDefinition,
    source: dict[str, Any],
    values: dict[str, Any],
) -> bool:
    for field_name, accepted in definition.applicable_when.items():
        value = values.get(field_name, source.get(field_name))
        if value not in accepted:
            return False
    return True


def _validate_json_value(value: Any, depth: int = 0) -> None:
    if depth > 10:
        raise ValueError("Intake nesting exceeds the supported depth")
    if isinstance(value, Mapping):
        if len(value) > MAX_INTAKE_ITEMS:
            raise ValueError("Intake object exceeds the collection limit")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 100:
                raise ValueError("Intake contains an invalid field name")
            _validate_json_value(item, depth + 1)
    elif isinstance(value, (list, tuple)):
        if len(value) > MAX_INTAKE_ITEMS:
            raise ValueError("Intake collection exceeds the collection limit")
        for item in value:
            _validate_json_value(item, depth + 1)
    elif isinstance(value, str):
        if len(value) > MAX_INTAKE_TEXT:
            raise ValueError("Intake contains oversized text")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Intake numbers must be finite")
    elif value is not None and not isinstance(value, (str, bool, int, float)):
        raise ValueError("Intake contains non-JSON data")


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else key
            flattened.update(_flatten(value[key], child))
        return flattened
    return {prefix: value}


def _load_builtin_adapters() -> None:
    import namengine.core.intake_adapters  # noqa: F401


def _canonical_slug(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9-]*", value))


def _canonical_field_name(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", value))


def _json_copy(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError("Value must be finite JSON data") from exc
