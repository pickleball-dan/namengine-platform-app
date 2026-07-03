"""Pet portrait generation for chosen-name keepsakes."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from namengine.core.storage import get_database_path, update_chosen_metadata


PORTRAIT_DIRNAME = "generated_pet_portraits"
DEFAULT_IMAGE_MODEL = "gpt-image-1"


def is_pet_portrait_generation_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and not _env_flag("NAMENGINE_DISABLE_PET_IMAGES")


def portrait_details_from_brief(brief: dict[str, Any] | None) -> dict[str, str]:
    inputs = (brief or {}).get("inputs", {})
    if not isinstance(inputs, dict):
        return {}

    details = {
        "breed": _clean(inputs.get("pet_breed")),
        "color": _clean(inputs.get("pet_color")),
        "life_stage": _clean(inputs.get("pet_life_stage")),
    }
    return {key: value for key, value in details.items() if value}


def pet_portrait_url_from_metadata(chosen_id: str, metadata: dict[str, Any]) -> str | None:
    portrait = metadata.get("pet_portrait") if isinstance(metadata, dict) else None
    if not isinstance(portrait, dict):
        return None

    filename = portrait.get("filename")
    if not filename:
        return None

    path = _portrait_path(str(filename))
    if path.is_file():
        return f"/generated/pet-portraits/{path.name}"
    return None


def ensure_pet_portrait_for_chosen(
    chosen: dict[str, Any],
    result: dict[str, Any],
    session: dict[str, Any] | None,
) -> dict[str, Any] | None:
    metadata = chosen.get("metadata") if isinstance(chosen.get("metadata"), dict) else {}
    existing_url = pet_portrait_url_from_metadata(str(chosen["id"]), metadata)
    if existing_url:
        portrait = dict(metadata["pet_portrait"])
        portrait["url"] = existing_url
        return portrait

    brief = _json_loads((session or {}).get("brief_json", "{}"))
    details = portrait_details_from_brief(brief)
    if not _has_enough_detail(details):
        return None

    portrait = {
        "details": details,
        "prompt": build_pet_portrait_prompt(chosen, result, brief, details),
        "status": "pending",
    }

    if not is_pet_portrait_generation_configured():
        portrait["status"] = "not_configured"
        return portrait

    filename = f"{chosen['id']}.png"
    path = _portrait_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    response = OpenAI().images.generate(
        model=os.getenv("NAMENGINE_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
        prompt=portrait["prompt"],
        size=os.getenv("NAMENGINE_IMAGE_SIZE", "1024x1024"),
    )
    image_data = response.data[0].b64_json
    if not image_data:
        raise RuntimeError("image response did not include base64 data")

    path.write_bytes(base64.b64decode(image_data))
    portrait.update(
        {
            "filename": filename,
            "status": "ready",
            "url": f"/generated/pet-portraits/{filename}",
        }
    )
    update_chosen_metadata(
        str(chosen["id"]),
        {"pet_portrait": {key: value for key, value in portrait.items() if key != "url"}},
    )
    return portrait


def build_pet_portrait_prompt(
    chosen: dict[str, Any],
    result: dict[str, Any],
    brief: dict[str, Any],
    details: dict[str, str] | None = None,
) -> str:
    inputs = brief.get("inputs", {}) if isinstance(brief, dict) else {}
    details = details or portrait_details_from_brief(brief)
    pet_type = _clean(inputs.get("pet_type")) or "pet"
    breed = details.get("breed") or pet_type
    color = details.get("color") or "natural"
    life_stage = details.get("life_stage") or "adult"
    personality = _clean(inputs.get("vibe")) or "warm"
    style = _clean(inputs.get("style")) or "timeless"
    name = _clean(chosen.get("name")) or _clean(result.get("name")) or "the pet"

    return (
        "Create a timeless framed studio portrait of a beloved pet. "
        f"Subject: a {color} {life_stage.lower()} {breed} {pet_type.lower()} named {name}. "
        f"Mood: {personality.lower()}, {style.lower()}, warm, dignified, emotionally inviting. "
        "Composition: centered head-and-shoulders portrait, natural expression, soft eyes, "
        "classic painted-photo look, subtle cream background, tasteful archival frame feeling, "
        "premium keepsake quality, realistic fur texture, gentle studio light. "
        "Do not include words, captions, logos, watermarks, collars with readable text, or signage."
    )


def _has_enough_detail(details: dict[str, str]) -> bool:
    return bool(details.get("breed") or details.get("color") or details.get("life_stage"))


def _portrait_path(filename: str) -> Path:
    safe_name = Path(filename).name
    return get_database_path().parent / PORTRAIT_DIRNAME / safe_name


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _json_loads(value: Any) -> dict[str, Any]:
    import json

    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
