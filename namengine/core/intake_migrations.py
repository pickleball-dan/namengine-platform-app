"""Deterministic migration chains for versioned vertical intake."""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import Any


MigrationFunction = Callable[[dict[str, Any]], tuple[dict[str, Any], list[str]]]


class IntakeMigrationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class IntakeMigration:
    vertical: str
    source_version: str
    destination_version: str
    migrate: MigrationFunction
    deprecated_field_mapping: dict[str, str]

    def __post_init__(self) -> None:
        if not _canonical_slug(self.vertical):
            raise ValueError("Migration vertical must be a canonical slug")
        if not self.source_version.strip() or not self.destination_version.strip():
            raise ValueError("Migration versions must be non-empty")
        if self.source_version == self.destination_version:
            raise ValueError("Migration source and destination must differ")


@dataclass(frozen=True, slots=True)
class IntakeMigrationResult:
    vertical: str
    source_version: str
    destination_version: str
    payload: dict[str, Any]
    warnings: tuple[str, ...]
    history: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "vertical": self.vertical,
            "source_version": self.source_version,
            "destination_version": self.destination_version,
            "payload": _json_copy(self.payload),
            "warnings": list(self.warnings),
            "history": list(self.history),
        }


_MIGRATIONS: dict[tuple[str, str], IntakeMigration] = {}
_LOCK = RLock()


def register_intake_migration(migration: IntakeMigration) -> None:
    key = (migration.vertical, migration.source_version)
    with _LOCK:
        existing = _MIGRATIONS.get(key)
        if existing is not None and existing != migration:
            raise ValueError(
                f"A migration already exists for {migration.vertical}/{migration.source_version}"
            )
        if _path_exists(
            migration.vertical,
            migration.destination_version,
            migration.source_version,
        ):
            raise ValueError("Intake migration would create a cycle")
        _MIGRATIONS[key] = migration


def unregister_intake_migration(vertical: str, source_version: str) -> None:
    with _LOCK:
        _MIGRATIONS.pop((vertical.strip().lower(), source_version.strip()), None)


def migrate_intake(
    vertical: str,
    payload: dict[str, Any],
    source_version: str,
    destination_version: str,
) -> IntakeMigrationResult:
    slug = vertical.strip().lower()
    if source_version == destination_version:
        return IntakeMigrationResult(
            slug,
            source_version,
            destination_version,
            _json_copy(payload),
            (),
            (),
        )
    chain = _migration_chain(slug, source_version, destination_version)
    current = _json_copy(payload)
    warnings: list[str] = []
    history: list[str] = []
    for migration in chain:
        current, step_warnings = migration.migrate(_json_copy(current))
        if not isinstance(current, dict):
            raise IntakeMigrationError("Migration returned a non-object payload")
        current = _json_copy(current)
        warnings.extend(_bounded_warning(item) for item in step_warnings)
        history.append(f"{migration.source_version}->{migration.destination_version}")
    return IntakeMigrationResult(
        slug,
        source_version,
        destination_version,
        current,
        tuple(warnings),
        tuple(history),
    )


def list_intake_migrations(vertical: str | None = None) -> tuple[dict[str, str], ...]:
    with _LOCK:
        migrations = sorted(
            _MIGRATIONS.values(),
            key=lambda item: (item.vertical, item.source_version, item.destination_version),
        )
    return tuple(
        {
            "vertical": item.vertical,
            "source_version": item.source_version,
            "destination_version": item.destination_version,
        }
        for item in migrations
        if vertical is None or item.vertical == vertical
    )


def _migration_chain(
    vertical: str, source_version: str, destination_version: str
) -> list[IntakeMigration]:
    with _LOCK:
        candidates = [item for item in _MIGRATIONS.values() if item.vertical == vertical]
    by_source: dict[str, list[IntakeMigration]] = {}
    for item in candidates:
        by_source.setdefault(item.source_version, []).append(item)
    queue = deque([(source_version, [])])
    visited: set[str] = set()
    while queue:
        version, chain = queue.popleft()
        if version in visited:
            continue
        visited.add(version)
        for migration in sorted(
            by_source.get(version, []), key=lambda item: item.destination_version
        ):
            next_chain = chain + [migration]
            if migration.destination_version == destination_version:
                return next_chain
            queue.append((migration.destination_version, next_chain))
    raise IntakeMigrationError(
        f"No migration path for {vertical}: {source_version} -> {destination_version}"
    )


def _path_exists(vertical: str, source_version: str, destination_version: str) -> bool:
    if source_version == destination_version:
        return True
    try:
        _migration_chain(vertical, source_version, destination_version)
    except IntakeMigrationError:
        return False
    return True


def _canonical_slug(value: str) -> bool:
    return bool(value) and value == value.strip().lower() and all(
        character.isalnum() or character == "-" for character in value
    )


def _json_copy(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise IntakeMigrationError("Migration payload must be finite JSON data") from exc


def _bounded_warning(value: Any) -> str:
    return str(value).strip()[:500]
