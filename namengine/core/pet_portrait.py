"""Pet portrait generation for chosen-name keepsakes."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from namengine.core.storage import get_database_path, update_chosen_metadata


PORTRAIT_DIRNAME = "generated_pet_portraits"
BABY_KEEPSAKE_DIRNAME = "generated_baby_keepsakes"
DEFAULT_IMAGE_MODEL = "gpt-image-1"


def is_pet_portrait_generation_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and not _env_flag("NAMENGINE_DISABLE_PET_IMAGES")


def is_keepsake_generation_configured(vertical_slug: str) -> bool:
    if not os.getenv("OPENAI_API_KEY"):
        return False
    if vertical_slug == "pet":
        return not _env_flag("NAMENGINE_DISABLE_PET_IMAGES")
    if vertical_slug == "baby":
        return not _env_flag("NAMENGINE_DISABLE_BABY_IMAGES")
    return False


def pet_portrait_runtime_config() -> dict[str, Any]:
    return keepsake_runtime_config("pet")


def keepsake_runtime_config(vertical_slug: str) -> dict[str, Any]:
    return {
        "configured": is_keepsake_generation_configured(vertical_slug),
        "has_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "disabled": _env_flag("NAMENGINE_DISABLE_PET_IMAGES")
        if vertical_slug == "pet"
        else _env_flag("NAMENGINE_DISABLE_BABY_IMAGES"),
        "model": os.getenv("NAMENGINE_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
        "size": os.getenv("NAMENGINE_IMAGE_SIZE", "1024x1024"),
    }


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


def keepsake_url_from_metadata(
    chosen_id: str,
    metadata: dict[str, Any],
    vertical_slug: str,
) -> str | None:
    metadata_key = _metadata_key(vertical_slug)
    keepsake = metadata.get(metadata_key) if isinstance(metadata, dict) else None
    if not isinstance(keepsake, dict):
        return None

    filename = keepsake.get("filename")
    if not filename:
        return None

    path = _keepsake_path(str(filename), vertical_slug)
    if path.is_file():
        return f"/generated/{_generated_route_segment(vertical_slug)}/{path.name}"
    return None


def pet_portrait_preview_for_chosen(
    chosen: dict[str, Any],
    session: dict[str, Any] | None,
) -> dict[str, Any] | None:
    return keepsake_preview_for_chosen(chosen, session)


def keepsake_preview_for_chosen(
    chosen: dict[str, Any],
    session: dict[str, Any] | None,
) -> dict[str, Any] | None:
    vertical_slug = str(chosen.get("vertical", ""))
    if vertical_slug not in {"pet", "baby"}:
        return None

    metadata = chosen.get("metadata") if isinstance(chosen.get("metadata"), dict) else {}
    metadata_key = _metadata_key(vertical_slug)
    portrait = metadata.get(metadata_key) if isinstance(metadata, dict) else None
    if isinstance(portrait, dict):
        portrait = dict(portrait)
        existing_url = keepsake_url_from_metadata(str(chosen["id"]), metadata, vertical_slug)
        if existing_url:
            portrait["url"] = existing_url
        return portrait

    brief = _json_loads((session or {}).get("brief_json", "{}"))
    details = keepsake_details_from_brief(brief, vertical_slug)
    if not _has_enough_detail(details):
        return None

    return {
        "details": details,
        "model": os.getenv("NAMENGINE_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
        "size": os.getenv("NAMENGINE_IMAGE_SIZE", "1024x1024"),
        "status": "pending" if is_keepsake_generation_configured(vertical_slug) else "not_configured",
        "kind": _keepsake_kind(vertical_slug),
    }


def prepare_pet_portrait_for_chosen(
    chosen: dict[str, Any],
    result: dict[str, Any],
    session: dict[str, Any] | None,
) -> dict[str, Any] | None:
    return prepare_keepsake_for_chosen(chosen, result, session)


def prepare_keepsake_for_chosen(
    chosen: dict[str, Any],
    result: dict[str, Any],
    session: dict[str, Any] | None,
) -> dict[str, Any] | None:
    vertical_slug = str(chosen.get("vertical", ""))
    if vertical_slug not in {"pet", "baby"}:
        return None

    metadata = chosen.get("metadata") if isinstance(chosen.get("metadata"), dict) else {}
    metadata_key = _metadata_key(vertical_slug)
    portrait = metadata.get(metadata_key) if isinstance(metadata, dict) else None
    if isinstance(portrait, dict) and portrait.get("status") in {"pending", "ready"}:
        return keepsake_preview_for_chosen(chosen, session)

    brief = _json_loads((session or {}).get("brief_json", "{}"))
    details = keepsake_details_from_brief(brief, vertical_slug)
    if not _has_enough_detail(details):
        return None

    portrait = {
        "details": details,
        "prompt": build_keepsake_prompt(chosen, result, brief, details, vertical_slug),
        "model": os.getenv("NAMENGINE_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
        "size": os.getenv("NAMENGINE_IMAGE_SIZE", "1024x1024"),
        "status": "pending" if is_keepsake_generation_configured(vertical_slug) else "not_configured",
        "kind": _keepsake_kind(vertical_slug),
    }
    update_chosen_metadata(
        str(chosen["id"]),
        {metadata_key: {key: value for key, value in portrait.items() if key != "prompt"}},
    )
    return portrait


def ensure_pet_portrait_for_chosen(
    chosen: dict[str, Any],
    result: dict[str, Any],
    session: dict[str, Any] | None,
) -> dict[str, Any] | None:
    return ensure_keepsake_for_chosen(chosen, result, session)


def ensure_keepsake_for_chosen(
    chosen: dict[str, Any],
    result: dict[str, Any],
    session: dict[str, Any] | None,
) -> dict[str, Any] | None:
    vertical_slug = str(chosen.get("vertical", ""))
    if vertical_slug not in {"pet", "baby"}:
        return None

    metadata = chosen.get("metadata") if isinstance(chosen.get("metadata"), dict) else {}
    metadata_key = _metadata_key(vertical_slug)
    existing_url = keepsake_url_from_metadata(str(chosen["id"]), metadata, vertical_slug)
    if existing_url:
        portrait = dict(metadata[metadata_key])
        portrait["url"] = existing_url
        return portrait

    brief = _json_loads((session or {}).get("brief_json", "{}"))
    details = keepsake_details_from_brief(brief, vertical_slug)
    if not _has_enough_detail(details):
        return None

    portrait = {
        "details": details,
        "prompt": build_keepsake_prompt(chosen, result, brief, details, vertical_slug),
        "model": os.getenv("NAMENGINE_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
        "size": os.getenv("NAMENGINE_IMAGE_SIZE", "1024x1024"),
        "status": "pending",
        "kind": _keepsake_kind(vertical_slug),
    }

    if not is_keepsake_generation_configured(vertical_slug):
        portrait["status"] = "not_configured"
        update_chosen_metadata(
            str(chosen["id"]),
            {metadata_key: {key: value for key, value in portrait.items() if key != "prompt"}},
        )
        return portrait

    filename = f"{chosen['id']}.png"
    path = _keepsake_path(filename, vertical_slug)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = OpenAI().images.generate(
            model=portrait["model"],
            prompt=portrait["prompt"],
            size=portrait["size"],
        )
    except Exception as exc:
        portrait.update(
            {
                "status": "failed",
                "error_type": exc.__class__.__name__,
                "error_message": _safe_error_message(exc),
            }
        )
        update_chosen_metadata(
            str(chosen["id"]),
            {metadata_key: {key: value for key, value in portrait.items() if key != "prompt"}},
        )
        raise

    image_data = response.data[0].b64_json
    if not image_data:
        error = RuntimeError("image response did not include base64 data")
        portrait.update(
            {
                "status": "failed",
                "error_type": error.__class__.__name__,
                "error_message": str(error),
            }
        )
        update_chosen_metadata(
            str(chosen["id"]),
            {metadata_key: {key: value for key, value in portrait.items() if key != "prompt"}},
        )
        raise error

    path.write_bytes(base64.b64decode(image_data))
    portrait.update(
        {
            "filename": filename,
            "status": "ready",
            "url": f"/generated/{_generated_route_segment(vertical_slug)}/{filename}",
        }
    )
    update_chosen_metadata(
        str(chosen["id"]),
        {metadata_key: {key: value for key, value in portrait.items() if key != "url"}},
    )
    return portrait


def build_pet_portrait_prompt(
    chosen: dict[str, Any],
    result: dict[str, Any],
    brief: dict[str, Any],
    details: dict[str, str] | None = None,
) -> str:
    return build_keepsake_prompt(chosen, result, brief, details, "pet")


def build_keepsake_prompt(
    chosen: dict[str, Any],
    result: dict[str, Any],
    brief: dict[str, Any],
    details: dict[str, str] | None = None,
    vertical_slug: str = "pet",
) -> str:
    if vertical_slug == "baby":
        return build_baby_keepsake_prompt(chosen, result, brief, details)

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


def build_baby_keepsake_prompt(
    chosen: dict[str, Any],
    result: dict[str, Any],
    brief: dict[str, Any],
    details: dict[str, str] | None = None,
) -> str:
    inputs = brief.get("inputs", {}) if isinstance(brief, dict) else {}
    details = details or keepsake_details_from_brief(brief, "baby")
    name = _clean(chosen.get("name")) or _clean(result.get("name")) or "the name"
    gender = (details.get("gender") or "neutral").lower()
    style = _clean(inputs.get("style")) or "classic"
    sound = _clean(inputs.get("sound")) or "warm"
    palette = _baby_palette(gender)

    return (
        "Create a premium nursery keepsake image centered on a soft baby blanket. "
        f"The blanket should have the name {name} tastefully embroidered on it in clear, readable letters. "
        f"Use a {palette} color palette based on the gender direction: {gender}. "
        f"Mood: {style.lower()}, {sound.lower()}, tender, refined, gift-worthy, modern heirloom. "
        "Composition: folded or gently draped blanket, subtle nursery surface, soft natural light, "
        "high-end product photography, cozy texture, no baby, no people, no hands. "
        "Do not include logos, watermarks, extra captions, misspellings, or unrelated text."
    )


def _has_enough_detail(details: dict[str, str]) -> bool:
    return bool(
        details.get("breed")
        or details.get("color")
        or details.get("life_stage")
        or details.get("gender")
        or details.get("style")
    )


def _portrait_path(filename: str) -> Path:
    safe_name = Path(filename).name
    return get_database_path().parent / PORTRAIT_DIRNAME / safe_name


def keepsake_details_from_brief(
    brief: dict[str, Any] | None,
    vertical_slug: str,
) -> dict[str, str]:
    if vertical_slug == "pet":
        return portrait_details_from_brief(brief)

    inputs = (brief or {}).get("inputs", {})
    if not isinstance(inputs, dict):
        return {}

    details = {
        "gender": _clean(inputs.get("gender")),
        "style": _clean(inputs.get("style")),
        "sound": _clean(inputs.get("sound")),
    }
    return {key: value for key, value in details.items() if value}


def _keepsake_path(filename: str, vertical_slug: str) -> Path:
    safe_name = Path(filename).name
    dirname = BABY_KEEPSAKE_DIRNAME if vertical_slug == "baby" else PORTRAIT_DIRNAME
    return get_database_path().parent / dirname / safe_name


def _metadata_key(vertical_slug: str) -> str:
    return "baby_keepsake" if vertical_slug == "baby" else "pet_portrait"


def _generated_route_segment(vertical_slug: str) -> str:
    return "baby-keepsakes" if vertical_slug == "baby" else "pet-portraits"


def _keepsake_kind(vertical_slug: str) -> str:
    return "baby_blanket" if vertical_slug == "baby" else "pet_portrait"


def _baby_palette(gender: str) -> str:
    normalized = gender.lower()
    if "boy" in normalized:
        return "soft powder blue, warm white, and pale silver"
    if "girl" in normalized:
        return "soft blush pink, warm white, and pale champagne"
    return "warm ivory, sage, pale blue, and blush accents"


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return ""
    for marker in ("sk-", "OPENAI_API_KEY"):
        if marker in message:
            return "OpenAI image generation failed; see server logs for sanitized details."
    return message[:500]


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
