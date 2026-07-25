"""Pytest safety defaults for deterministic local tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _disable_live_openai_by_default(monkeypatch: pytest.MonkeyPatch):
    """Keep ordinary regression tests from spending real OpenAI calls.

    Tests that intentionally exercise AI behavior patch OPENAI_API_KEY or
    is_ai_generation_configured explicitly. Local/live provider proof should be
    run through a dedicated smoke script, not accidental inherited shell env.
    """
    if os.getenv("NAMENGINE_ALLOW_LIVE_OPENAI_IN_TESTS") != "1":
        monkeypatch.setenv("OPENAI_API_KEY", "")
