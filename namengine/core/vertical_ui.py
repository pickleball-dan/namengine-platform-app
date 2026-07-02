"""Shared UI contract helpers for vertical-specific presentation."""

from __future__ import annotations

from pathlib import Path

from namengine.core.schemas import VerticalConfig


REQUIRED_THEME_KEYS = ("accent", "surface", "page", "card", "ink", "muted")
REQUIRED_ASSET_KEYS = ("logo", "share_image")


def vertical_theme_style(vertical: VerticalConfig | None) -> str:
    if vertical is None:
        return ""

    declarations = []
    for key, value in vertical.theme.items():
        css_key = key.replace("_", "-")
        declarations.append(f"--{css_key}: {value}")
    return "; ".join(declarations)


def validate_vertical_ui_contract(vertical: VerticalConfig, static_root: str | Path) -> list[str]:
    errors: list[str] = []
    missing_theme = [key for key in REQUIRED_THEME_KEYS if key not in vertical.theme]
    missing_assets = [key for key in REQUIRED_ASSET_KEYS if key not in vertical.assets]

    if missing_theme:
        errors.append(f"{vertical.slug} missing theme keys: {', '.join(missing_theme)}")
    if missing_assets:
        errors.append(f"{vertical.slug} missing asset keys: {', '.join(missing_assets)}")

    static_path = Path(static_root)
    for key in REQUIRED_ASSET_KEYS:
        asset = vertical.assets.get(key)
        if asset and not (static_path / asset).exists():
            errors.append(f"{vertical.slug} missing {key} asset: {asset}")

    return errors
