"""SQLite storage boundary for local NamEngine platform development."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from namengine.core.schemas import (
    ChosenName,
    NameResult,
    NamingBrief,
    Reaction,
    TasteProfile,
    ValidationResult,
    to_plain_data,
    utc_now_iso,
)
from namengine.core.provider_performance import build_provider_performance


DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "namengine.sqlite3"


class StorageError(RuntimeError):
    pass


def get_database_path() -> Path:
    return Path(os.getenv("NAMENGINE_DB_PATH", DEFAULT_DB_PATH))


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path | None = None) -> None:
    with closing(connect(db_path)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                vertical TEXT NOT NULL,
                brief_json TEXT NOT NULL,
                round_number INTEGER NOT NULL DEFAULT 1,
                parent_session_id TEXT,
                refinement_prompt TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS name_results (
                id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                name TEXT NOT NULL,
                slug TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (session_id, id),
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reactions (
                session_id TEXT NOT NULL,
                result_id TEXT NOT NULL,
                value TEXT NOT NULL,
                reaction_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (session_id, result_id),
                FOREIGN KEY (session_id, result_id)
                    REFERENCES name_results(session_id, id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chosen_names (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                result_id TEXT NOT NULL,
                name TEXT NOT NULL,
                vertical TEXT NOT NULL,
                share_id TEXT NOT NULL,
                chosen_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id, result_id)
                    REFERENCES name_results(session_id, id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS taste_profiles (
                session_id TEXT PRIMARY KEY,
                vertical TEXT NOT NULL,
                profile_json TEXT NOT NULL,
                summary TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS validation_results (
                session_id TEXT NOT NULL,
                result_id TEXT NOT NULL,
                module TEXT NOT NULL,
                status TEXT NOT NULL,
                label TEXT NOT NULL,
                message TEXT NOT NULL,
                score REAL,
                validation_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (session_id, result_id, module),
                FOREIGN KEY (session_id, result_id)
                    REFERENCES name_results(session_id, id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS provider_performance (
                session_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                vertical TEXT NOT NULL,
                generated_count INTEGER NOT NULL,
                love_count INTEGER NOT NULL,
                maybe_count INTEGER NOT NULL,
                no_count INTEGER NOT NULL,
                chosen_count INTEGER NOT NULL,
                average_quality_score REAL NOT NULL,
                love_rate REAL NOT NULL,
                choose_rate REAL NOT NULL,
                performance_score REAL NOT NULL,
                performance_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (session_id, provider),
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            """
        )
        _ensure_column(connection, "sessions", "round_number", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(connection, "sessions", "parent_session_id", "TEXT")
        _ensure_column(connection, "sessions", "refinement_prompt", "TEXT")
        connection.commit()


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def save_session(
    session_id: str,
    vertical: str,
    brief: NamingBrief,
    results: list[NameResult],
    round_number: int = 1,
    parent_session_id: str | None = None,
    refinement_prompt: str | None = None,
    db_path: Path | None = None,
) -> None:
    initialize_database(db_path)
    now = utc_now_iso()
    with closing(connect(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO sessions
                (id, vertical, brief_json, round_number, parent_session_id,
                 refinement_prompt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                vertical = excluded.vertical,
                brief_json = excluded.brief_json,
                round_number = excluded.round_number,
                parent_session_id = excluded.parent_session_id,
                refinement_prompt = excluded.refinement_prompt,
                updated_at = excluded.updated_at
            """,
            (
                session_id,
                vertical,
                json.dumps(to_plain_data(brief)),
                round_number,
                parent_session_id,
                refinement_prompt,
                now,
                now,
            ),
        )

        for result in results:
            connection.execute(
                """
                INSERT INTO name_results
                    (id, session_id, name, slug, result_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, id) DO UPDATE SET
                    name = excluded.name,
                    slug = excluded.slug,
                    result_json = excluded.result_json
                """,
                (
                    result.id,
                    session_id,
                    result.name,
                    result.slug,
                    json.dumps(to_plain_data(result)),
                    now,
                ),
            )
            for validation in result.validation:
                connection.execute(
                    """
                    INSERT INTO validation_results
                        (session_id, result_id, module, status, label, message,
                         score, validation_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id, result_id, module) DO UPDATE SET
                        status = excluded.status,
                        label = excluded.label,
                        message = excluded.message,
                        score = excluded.score,
                        validation_json = excluded.validation_json
                    """,
                    (
                        session_id,
                        result.id,
                        validation.module,
                        validation.status.value,
                        validation.label,
                        validation.message,
                        validation.score,
                        json.dumps(to_plain_data(validation)),
                        now,
                    ),
                )
        connection.commit()


def save_reaction(reaction: Reaction, db_path: Path | None = None) -> None:
    initialize_database(db_path)
    now = utc_now_iso()
    try:
        with closing(connect(db_path)) as connection:
            connection.execute(
                """
                INSERT INTO reactions
                    (session_id, result_id, value, reaction_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, result_id) DO UPDATE SET
                    value = excluded.value,
                    reaction_json = excluded.reaction_json,
                    updated_at = excluded.updated_at
                """,
                (
                    reaction.session_id,
                    reaction.result_id,
                    reaction.value.value,
                    json.dumps(to_plain_data(reaction)),
                    reaction.created_at,
                    now,
                ),
            )
            connection.commit()
    except sqlite3.IntegrityError as exc:
        raise StorageError("session/result not found") from exc
    refresh_provider_performance(reaction.session_id, db_path)


def save_chosen_name(
    session_id: str,
    result_id: str,
    db_path: Path | None = None,
) -> ChosenName:
    initialize_database(db_path)
    now = utc_now_iso()
    with closing(connect(db_path)) as connection:
        row = connection.execute(
            """
            SELECT sessions.vertical, name_results.name
            FROM name_results
            JOIN sessions ON sessions.id = name_results.session_id
            WHERE name_results.session_id = ? AND name_results.id = ?
            """,
            (session_id, result_id),
        ).fetchone()
        if row is None:
            raise StorageError("session/result not found")

        chosen_id = _stable_id("chosen", session_id, result_id)
        chosen = ChosenName(
            id=chosen_id,
            session_id=session_id,
            result_id=result_id,
            name=str(row["name"]),
            vertical=str(row["vertical"]),
            share_id=chosen_id,
            created_at=now,
        )
        connection.execute(
            """
            INSERT INTO chosen_names
                (id, session_id, result_id, name, vertical, share_id, chosen_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                vertical = excluded.vertical,
                share_id = excluded.share_id,
                chosen_json = excluded.chosen_json
            """,
            (
                chosen.id,
                chosen.session_id,
                chosen.result_id,
                chosen.name,
                chosen.vertical,
                chosen.share_id or chosen.id,
                json.dumps(to_plain_data(chosen)),
                chosen.created_at,
            ),
        )
        connection.commit()

    refresh_provider_performance(session_id, db_path)
    return chosen


def refresh_provider_performance(
    session_id: str,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    snapshot = get_session_snapshot(session_id, db_path)
    if snapshot is None:
        raise StorageError("session not found")

    rows = [item.to_row() for item in build_provider_performance(snapshot)]
    now = utc_now_iso()
    with closing(connect(db_path)) as connection:
        for row in rows:
            connection.execute(
                """
                INSERT INTO provider_performance
                    (session_id, provider, vertical, generated_count, love_count,
                     maybe_count, no_count, chosen_count, average_quality_score,
                     love_rate, choose_rate, performance_score, performance_json,
                     updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, provider) DO UPDATE SET
                    vertical = excluded.vertical,
                    generated_count = excluded.generated_count,
                    love_count = excluded.love_count,
                    maybe_count = excluded.maybe_count,
                    no_count = excluded.no_count,
                    chosen_count = excluded.chosen_count,
                    average_quality_score = excluded.average_quality_score,
                    love_rate = excluded.love_rate,
                    choose_rate = excluded.choose_rate,
                    performance_score = excluded.performance_score,
                    performance_json = excluded.performance_json,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    row["provider"],
                    row["vertical"],
                    row["generated_count"],
                    row["love_count"],
                    row["maybe_count"],
                    row["no_count"],
                    row["chosen_count"],
                    row["average_quality_score"],
                    row["love_rate"],
                    row["choose_rate"],
                    row["performance_score"],
                    json.dumps(row),
                    now,
                ),
            )
        connection.commit()
    return rows


def save_taste_profile(
    profile: TasteProfile,
    db_path: Path | None = None,
) -> None:
    initialize_database(db_path)
    with closing(connect(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO taste_profiles
                (session_id, vertical, profile_json, summary, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                vertical = excluded.vertical,
                profile_json = excluded.profile_json,
                summary = excluded.summary,
                updated_at = excluded.updated_at
            """,
            (
                profile.session_id,
                profile.vertical,
                json.dumps(to_plain_data(profile)),
                profile.summary,
                profile.updated_at,
            ),
        )
        connection.commit()


def save_validation_results(
    session_id: str,
    result_id: str,
    validation: list[ValidationResult],
    db_path: Path | None = None,
) -> None:
    initialize_database(db_path)
    now = utc_now_iso()
    with closing(connect(db_path)) as connection:
        for item in validation:
            connection.execute(
                """
                INSERT INTO validation_results
                    (session_id, result_id, module, status, label, message,
                     score, validation_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, result_id, module) DO UPDATE SET
                    status = excluded.status,
                    label = excluded.label,
                    message = excluded.message,
                    score = excluded.score,
                    validation_json = excluded.validation_json
                """,
                (
                    session_id,
                    result_id,
                    item.module,
                    item.status.value,
                    item.label,
                    item.message,
                    item.score,
                    json.dumps(to_plain_data(item)),
                    now,
                ),
            )
        connection.commit()


def _stable_id(prefix: str, *parts: str) -> str:
    import hashlib

    digest = hashlib.sha1(":".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:12]}"


def get_reaction_counts(session_id: str, db_path: Path | None = None) -> dict[str, int]:
    initialize_database(db_path)
    counts = {"love": 0, "maybe": 0, "no": 0}
    with closing(connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT value, COUNT(*) AS count
            FROM reactions
            WHERE session_id = ?
            GROUP BY value
            """,
            (session_id,),
        ).fetchall()

    for row in rows:
        counts[str(row["value"])] = int(row["count"])
    return counts


def get_session_snapshot(session_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    initialize_database(db_path)
    with closing(connect(db_path)) as connection:
        session = connection.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if session is None:
            return None

        results = connection.execute(
            "SELECT * FROM name_results WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        reactions = connection.execute(
            "SELECT * FROM reactions WHERE session_id = ? ORDER BY result_id",
            (session_id,),
        ).fetchall()
        chosen = connection.execute(
            "SELECT * FROM chosen_names WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
        taste_profile = connection.execute(
            "SELECT * FROM taste_profiles WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        validation = connection.execute(
            """
            SELECT *
            FROM validation_results
            WHERE session_id = ?
            ORDER BY result_id, module
            """,
            (session_id,),
        ).fetchall()
        provider_performance = connection.execute(
            """
            SELECT *
            FROM provider_performance
            WHERE session_id = ?
            ORDER BY performance_score DESC
            """,
            (session_id,),
        ).fetchall()

    return {
        "session": dict(session),
        "results": [dict(row) for row in results],
        "reactions": [dict(row) for row in reactions],
        "chosen_names": [dict(row) for row in chosen],
        "taste_profile": dict(taste_profile) if taste_profile else None,
        "validation_results": [dict(row) for row in validation],
        "provider_performance": [dict(row) for row in provider_performance],
        "reaction_counts": get_reaction_counts(session_id, db_path),
    }


def get_provider_performance(
    session_id: str,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    initialize_database(db_path)
    with closing(connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM provider_performance
            WHERE session_id = ?
            ORDER BY performance_score DESC
            """,
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_validation_results(
    session_id: str,
    result_id: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    initialize_database(db_path)
    query = "SELECT * FROM validation_results WHERE session_id = ?"
    params: tuple[Any, ...] = (session_id,)
    if result_id is not None:
        query += " AND result_id = ?"
        params = (session_id, result_id)
    query += " ORDER BY result_id, module"
    with closing(connect(db_path)) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_taste_profile(session_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    initialize_database(db_path)
    with closing(connect(db_path)) as connection:
        row = connection.execute(
            "SELECT * FROM taste_profiles WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def get_session_chain_snapshots(session_id: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    current_id: str | None = session_id
    seen: set[str] = set()

    while current_id and current_id not in seen:
        seen.add(current_id)
        snapshot = get_session_snapshot(current_id, db_path)
        if snapshot is None:
            break
        chain.append(snapshot)
        current_id = snapshot["session"].get("parent_session_id")

    return list(reversed(chain))


def get_chosen_snapshot(chosen_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    initialize_database(db_path)
    with closing(connect(db_path)) as connection:
        chosen = connection.execute(
            "SELECT * FROM chosen_names WHERE id = ?",
            (chosen_id,),
        ).fetchone()
        if chosen is None:
            return None

        result = connection.execute(
            """
            SELECT *
            FROM name_results
            WHERE session_id = ? AND id = ?
            """,
            (chosen["session_id"], chosen["result_id"]),
        ).fetchone()
        session = connection.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (chosen["session_id"],),
        ).fetchone()

    return {
        "chosen": dict(chosen),
        "result": dict(result) if result else None,
        "session": dict(session) if session else None,
    }
