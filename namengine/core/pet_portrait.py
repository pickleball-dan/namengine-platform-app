"""Pet portrait generation for chosen-name keepsakes."""

from __future__ import annotations

import base64
import binascii
import os
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from openai import OpenAI

from namengine.core.storage import get_database_path, update_chosen_metadata


PORTRAIT_DIRNAME = "generated_pet_portraits"
BABY_KEEPSAKE_DIRNAME = "generated_baby_keepsakes"
BUSINESS_IMAGE_DIRNAME = "generated_business_images"
DEFAULT_IMAGE_MODEL = "gpt-image-1"
DEFAULT_IMAGE_RETENTION_DAYS = 30
IMAGE_VERTICALS = {"baby", "pet", "business"}


def is_pet_portrait_generation_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and not _env_flag("NAMENGINE_DISABLE_PET_IMAGES")


def is_keepsake_generation_configured(vertical_slug: str) -> bool:
    if vertical_slug not in IMAGE_VERTICALS or not os.getenv("OPENAI_API_KEY"):
        return False
    return not _env_flag(_disable_flag(vertical_slug))


def pet_portrait_runtime_config() -> dict[str, Any]:
    return keepsake_runtime_config("pet")


def keepsake_runtime_config(vertical_slug: str) -> dict[str, Any]:
    return {
        "configured": is_keepsake_generation_configured(vertical_slug),
        "has_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "disabled": _env_flag(_disable_flag(vertical_slug)) if vertical_slug in IMAGE_VERTICALS else True,
        "model": os.getenv("NAMENGINE_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
        "size": os.getenv("NAMENGINE_IMAGE_SIZE", "1024x1024"),
        "storage_configured": bool(os.getenv("NAMENGINE_GENERATED_IMAGE_DIR")),
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
    if vertical_slug not in IMAGE_VERTICALS:
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
    *,
    force_retry: bool = False,
) -> dict[str, Any] | None:
    vertical_slug = str(chosen.get("vertical", ""))
    if vertical_slug not in IMAGE_VERTICALS:
        return None

    metadata = chosen.get("metadata") if isinstance(chosen.get("metadata"), dict) else {}
    metadata_key = _metadata_key(vertical_slug)
    portrait = metadata.get(metadata_key) if isinstance(metadata, dict) else None
    if (
        isinstance(portrait, dict)
        and portrait.get("status") in {"pending", "ready", "failed"}
        and not (force_retry and portrait.get("status") == "failed")
    ):
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
    if vertical_slug not in IMAGE_VERTICALS:
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

    filename = f"{secrets.token_urlsafe(24)}.png"
    path = _keepsake_path(filename, vertical_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    cleanup_generated_images(vertical_slug)

    try:
        response = OpenAI().images.generate(
            model=portrait["model"],
            prompt=portrait["prompt"],
            size=portrait["size"],
            n=1,
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

    try:
        image_bytes = _image_bytes_from_response(response)
    except Exception as error:
        portrait.update(
            {
                "status": "failed",
                "error_type": error.__class__.__name__,
                "error_message": _safe_error_message(error),
            }
        )
        update_chosen_metadata(
            str(chosen["id"]),
            {metadata_key: {key: value for key, value in portrait.items() if key != "prompt"}},
        )
        raise error

    path.write_bytes(image_bytes)
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
    if vertical_slug == "business":
        return build_business_image_prompt(chosen, result, brief, details)

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


def build_business_image_prompt(
    chosen: dict[str, Any],
    result: dict[str, Any],
    brief: dict[str, Any],
    details: dict[str, str] | None = None,
) -> str:
    inputs = brief.get("inputs", {}) if isinstance(brief, dict) else {}
    details = details or keepsake_details_from_brief(brief, "business")
    name = _clean(chosen.get("name")) or _clean(result.get("name")) or "the business name"
    description = details.get("business_description") or "a growing business"
    industry = details.get("industry") or "its category"
    audience = details.get("audience") or "its ideal customers"
    style = details.get("style") or "credible and distinctive"
    tagline = _clean(result.get("tagline"))

    return (
        "Create a commercially useful premium brand-direction moodboard, not a logo, for a business named "
        f"{name}. Business: {description}. Category: {industry}. Audience: {audience}. "
        f"Brand direction: {style}. "
        + (f"Positioning inspiration: {tagline}. " if tagline else "")
        + "Translate the specific category, audience, and positioning into one coherent visual system. "
        "Composition: an art-directed square board with four to six coordinated zones showing a concise color palette, "
        "materials or texture, category-relevant environment or object photography, a distinctive non-letterform graphic motif, "
        "and a blank real-world application surface such as stationery, packaging, storefront, or social tile. "
        "It should help a founder evaluate a credible visual direction, not look like generic decorative abstract art. "
        "Use commercially sophisticated art direction and intentional negative space. "
        "Do not render the business name or any words, letters, initials, monograms, logo marks, trademarks, "
        "watermarks, or readable text. The abstract motif must not resemble a letter or typographic character."
    )


def _has_enough_detail(details: dict[str, str]) -> bool:
    return bool(
        details.get("breed")
        or details.get("color")
        or details.get("life_stage")
        or details.get("gender")
        or details.get("style")
        or details.get("business_description")
        or details.get("audience")
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

    if vertical_slug == "business":
        details = {
            "business_description": _clean(inputs.get("business_description")),
            "industry": _clean(inputs.get("industry")),
            "audience": _clean(inputs.get("audience")),
            "style": _clean(inputs.get("style")),
        }
    else:
        details = {
            "gender": _clean(inputs.get("gender")),
            "style": _clean(inputs.get("style")),
            "sound": _clean(inputs.get("sound")),
        }
    return {key: value for key, value in details.items() if value}


def _keepsake_path(filename: str, vertical_slug: str) -> Path:
    safe_name = Path(filename).name
    dirname = {
        "baby": BABY_KEEPSAKE_DIRNAME,
        "business": BUSINESS_IMAGE_DIRNAME,
        "pet": PORTRAIT_DIRNAME,
    }[vertical_slug]
    configured_root = os.getenv("NAMENGINE_GENERATED_IMAGE_DIR", "").strip()
    root = Path(configured_root) if configured_root else get_database_path().parent
    return root / dirname / safe_name


def _metadata_key(vertical_slug: str) -> str:
    return {
        "baby": "baby_keepsake",
        "business": "business_image",
        "pet": "pet_portrait",
    }[vertical_slug]


def _generated_route_segment(vertical_slug: str) -> str:
    return {
        "baby": "baby-keepsakes",
        "business": "business-images",
        "pet": "pet-portraits",
    }[vertical_slug]


def _keepsake_kind(vertical_slug: str) -> str:
    return {
        "baby": "baby_blanket",
        "business": "business_brand_concept",
        "pet": "pet_portrait",
    }[vertical_slug]


def generated_image_directory(vertical_slug: str) -> Path:
    return _keepsake_path("placeholder", vertical_slug).parent


def cleanup_generated_images(vertical_slug: str, *, now: float | None = None) -> int:
    directory = generated_image_directory(vertical_slug)
    if not directory.is_dir():
        return 0
    retention_days = _positive_int_env(
        "NAMENGINE_IMAGE_RETENTION_DAYS", DEFAULT_IMAGE_RETENTION_DAYS
    )
    cutoff = (now if now is not None else time.time()) - retention_days * 86400
    removed = 0
    for candidate in directory.glob("*.png"):
        try:
            if candidate.is_file() and candidate.stat().st_mtime < cutoff:
                candidate.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def _disable_flag(vertical_slug: str) -> str:
    return {
        "baby": "NAMENGINE_DISABLE_BABY_IMAGES",
        "business": "NAMENGINE_DISABLE_BUSINESS_IMAGES",
        "pet": "NAMENGINE_DISABLE_PET_IMAGES",
    }[vertical_slug]


def _image_bytes_from_response(response: Any) -> bytes:
    data = response.get("data") if isinstance(response, dict) else getattr(response, "data", None)
    if not data:
        raise RuntimeError("Image provider returned no image data.")
    item = data[0]
    encoded = item.get("b64_json") if isinstance(item, dict) else getattr(item, "b64_json", None)
    if encoded:
        try:
            return base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise RuntimeError("Image provider returned invalid image data.") from exc
    image_url = item.get("url") if isinstance(item, dict) else getattr(item, "url", None)
    if image_url:
        with urlopen(str(image_url), timeout=30) as remote_image:  # nosec: provider-owned response URL
            return remote_image.read()
    raise RuntimeError("Image provider response did not contain an image.")


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
    if isinstance(exc, RuntimeError) and str(exc).startswith("Image provider"):
        return str(exc)
    return "Image creation failed. Please try again."


def safe_provider_error_for_log(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    request_id = getattr(exc, "request_id", None)
    parts = [exc.__class__.__name__]
    if status is not None:
        parts.append(f"status={status}")
    if request_id:
        parts.append(f"request_id={request_id}")
    return " ".join(parts)


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _positive_int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def _json_loads(value: Any) -> dict[str, Any]:
    import json

    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
