"""NamEngine application entry point with internal audit routes."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from typing import Any

from flask import render_template, request

from app import app
from namengine.core import get_database_path, initialize_database


def _safe_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _recent_audit_sessions(vertical: str, limit: int) -> list[dict[str, Any]]: