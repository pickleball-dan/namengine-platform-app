"""Platform registry for versioned generation prompts."""

from __future__ import annotations


DEFAULT_PROMPT_VERSION = "namengine-taste-engine-v1"
BABY_PROMPT_VERSION = "namengine-baby-quality-v1"
_BUILTIN_PROMPT_VERSIONS = {"baby": BABY_PROMPT_VERSION}
_PROMPT_VERSIONS: dict[str, str] = dict(_BUILTIN_PROMPT_VERSIONS)


def register_prompt_version(vertical_slug: str, version: str) -> None:
    """Register the active prompt version for a vertical."""
    slug = vertical_slug.strip().lower()
    clean_version = version.strip()
    if not slug or not clean_version:
        raise ValueError("Prompt version registrations require a vertical and version")
    _PROMPT_VERSIONS[slug] = clean_version


def unregister_prompt_version(vertical_slug: str) -> None:
    """Remove a dynamic registration while preserving platform defaults."""
    slug = vertical_slug.strip().lower()
    if slug in _BUILTIN_PROMPT_VERSIONS:
        _PROMPT_VERSIONS[slug] = _BUILTIN_PROMPT_VERSIONS[slug]
    else:
        _PROMPT_VERSIONS.pop(slug, None)


def prompt_version_for(vertical_slug: str) -> str:
    return _PROMPT_VERSIONS.get(vertical_slug.strip().lower(), DEFAULT_PROMPT_VERSION)


def registered_prompt_versions() -> dict[str, str]:
    return dict(_PROMPT_VERSIONS)
