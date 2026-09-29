"""Magic link token generation and session state management for NamEngine."""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Any

from namengine.core.storage import (
    get_magic_link,
    mark_magic_link_used,
    save_magic_link,
)

MAGIC_LINK_EXPIRY_DAYS = 30
TOKEN_BYTES = 32


def generate_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def create_magic_link(
    *,
    email: str,
    vertical: str,
    session_id: str,
    session_state: dict[str, Any],
) -> str:
    """Create a magic link token, persist it, and return the token string."""
    token = generate_token()
    expires_at = (datetime.utcnow() + timedelta(days=MAGIC_LINK_EXPIRY_DAYS)).isoformat()
    save_magic_link(
        token=token,
        email=email,
        vertical=vertical,
        session_id=session_id,
        session_state_json=json.dumps(session_state),
        expires_at=expires_at,
    )
    return token


def build_magic_url(token: str, base_url: str) -> str:
    """Build the full magic link URL."""
    base = base_url.rstrip("/")
    return f"{base}/continue/{token}"


def validate_and_consume_token(token: str) -> dict[str, Any] | None:
    """
    Validate a magic link token. Returns the link record (with parsed session_state)
    if valid and not expired. Marks the token as used. Returns None if invalid/expired.
    Allows re-use (does not block on used_at) so partners can share the same link.
    """
    record = get_magic_link(token)
    if not record:
        return None

    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.utcnow() > expires_at:
        return None

    # Mark used (non-blocking — partners can still use the same link)
    mark_magic_link_used(token)

    record["session_state"] = json.loads(record["session_state_json"])
    return record
