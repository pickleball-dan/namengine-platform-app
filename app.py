"""Thin Flask shell for the shared NamEngine platform."""

from __future__ import annotations

import logging
import os
import re
import time
from secrets import token_urlsafe
from datetime import datetime, timedelta, timezone
from base64 import b64encode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from hmac import compare_digest, new as hmac_new
from threading import Lock, Thread
from hashlib import sha1
from urllib.parse import urlencode, urlparse, urljoin

from flask import Flask, abort, g, jsonify, make_response, redirect, render_template, request, send_from_directory, url_for

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - Render uses real env vars; local dev may skip dotenv
    load_dotenv = None

from namengine import CONTRACT_VERSION
from namengine.core.intake_limits import (
    OTHER_CHOICE_MAX_LENGTH,
    REFINEMENT_INSTRUCTION_MAX_LENGTH,
    clip_intake_value,
    clip_text,
    intake_field_max_length,
)
from namengine.core import (
    AIGenerationError,
    ReactionError,
    build_brief,
    build_compare_items,
    build_public_reaction,
    build_taste_profile,
    build_trust_cue,
    compare_contrast_groups,
    ensure_keepsake_for_chosen,
    generate_names,
    generate_with_router,
    get_failed_generation_audits,
    get_reaction_counts,
    get_recent_audit_sessions,
    is_ai_generation_configured,
    get_chosen_snapshot,
    get_database_path,
    generated_image_directory,
    get_session_snapshot,
    keepsake_preview_for_chosen,
    get_taste_profile,
    keepsake_runtime_config,
    load_taste_engine_fixtures,
    ModelProvider,
    prepare_keepsake_for_chosen,
    safe_provider_error_for_log,
    refine_session,
    run_taste_engine_fixture_set,
    save_reaction,
    save_chosen_name,
    save_failed_generation_audit,
    save_session,
    StorageError,
    summarize_taste_engine_eval,
    vertical_theme_style,
)
from namengine.core.name_facts import build_name_fact_card
from namengine.core.baby_decision_support import build_baby_decision_support
from namengine.core.storage import get_session_chain_snapshots
from namengine.core.storage import (
    get_beta_usage,
    save_beta_email_capture,
    save_beta_usage_email,
    save_beta_usage_free_session,
)
from namengine.core.taste_evolution import build_taste_evolution
from namengine.core.ai_generation import DEFAULT_MODEL
from namengine.core.cost_estimates import estimate_ai_calls_cost_usd
from namengine.core.domain_availability import enrich_business_domain_info
from namengine.core.mission_control_telemetry import build_openai_usage_report
from namengine.core.prompt_versions import prompt_version_for
from namengine.core.schemas import NameResult, NamingBrief, ValidationResult, to_plain_data
from namengine.core.validation import filter_results_for_brief
from namengine.verticals import VERTICALS, get_vertical


logger = logging.getLogger(__name__)
_LOCAL_BETA_ACCESS_SECRET = token_urlsafe(32)
_portrait_jobs: set[str] = set()
_portrait_jobs_lock = Lock()
MIN_REACTIONS_FOR_REFINEMENT = 3
BETA_VISITOR_COOKIE_NAME = "namengine_beta_visitor_id"
BETA_FREE_ACCESS_HOURS_DEFAULT = 24
BETA_EMAIL_MAX_LENGTH = 254
BETA_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class NameGenerationUnavailable(RuntimeError):
    """Raised when the production naming engine cannot return honest LLM results."""


class FreeGenerationAccessRequired(RuntimeError):
    """Raised when a free visitor tries to generate another first-round list."""

    def __init__(self, session_id: str):
        super().__init__(session_id)
        self.session_id = session_id


_UNHELPFUL_CARD_VALUES = {
    "unknown",
    "not available",
    "not applicable",
    "n/a",
    "none",
    "tbd",
}


def meaningful_card_text(value) -> str:
    """Return useful customer-facing summary text, excluding placeholders."""
    text = " ".join(str(value or "").split()).strip()
    lowered = text.lower().rstrip(".")
    if not text or lowered in _UNHELPFUL_CARD_VALUES:
        return ""
    if any(
        marker in lowered
        for marker in (
            "data is being expanded",
            "coming soon",
            "beta placeholder",
            "name shaped for",
        )
    ):
        return ""
    return text


def compact_card_text(value, max_length: int = 72) -> str:
    """Return a short first-run card snippet without changing the underlying detail text."""
    text = meaningful_card_text(value)
    if not text or len(text) <= max_length:
        return text
    clipped = text[: max_length + 1].rsplit(" ", 1)[0].strip(" ,;:-")
    return f"{clipped}…" if clipped else text[:max_length].rstrip() + "…"


def collapsed_result_meaning(result) -> str:
    """Read a concise meaning without inferring one from generic origin prose."""
    direct = result.get("meaning") if isinstance(result, dict) else getattr(result, "meaning", "")
    meaning = meaningful_card_text(direct)
    if meaning:
        return meaning

    metadata = result.get("metadata", {}) if isinstance(result, dict) else getattr(result, "metadata", {})
    if not isinstance(metadata, dict):
        return ""
    meaning = meaningful_card_text(metadata.get("meaning"))
    if meaning:
        return meaning

    combined = meaningful_card_text(metadata.get("meaning_and_origin") or metadata.get("origin_meaning"))
    if not combined:
        return ""
    match = re.search(r"(?:^|[;|])\s*meaning\s*:\s*([^;|]+)", combined, flags=re.IGNORECASE)
    return meaningful_card_text(match.group(1)) if match else ""




def grouped_questions(vertical) -> list[dict]:
    groups: list[dict] = []
    by_section: dict[str, list] = {}

    for question in vertical.intake_questions:
        section = question.section or "Tell us what matters"
        if section not in by_section:
            by_section[section] = []
            groups.append({"title": section, "questions": by_section[section]})
        by_section[section].append(question)

    return groups


def feeling_section_titles(vertical) -> list[str]:
    return [group["title"] for group in grouped_questions(vertical) if group["title"] != "Tell us what matters"]


def feelings_scale_enabled(vertical) -> bool:
    if vertical.slug == "pet":
        return False
    return len(feeling_section_titles(vertical)) >= 2


def section_strength_field(section_title: str) -> str:
    return "taste_strength_" + slugify_for_field(section_title)


def slugify_for_field(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.lower()).strip("_") or "section"


def feeling_center_icon(vertical, source=None) -> dict[str, str]:
    source = source or {}
    if vertical.slug == "baby":
        return {"kind": "baby", "noun": "baby", "label": "baby"}
    if vertical.slug == "business":
        return {"kind": "building", "noun": "building", "label": "building"}
    if vertical.slug == "product":
        return {"kind": "product", "noun": "product", "label": "product"}
    if vertical.slug == "pet":
        pet_type = str(source.get("pet_type") or source.get("species") or "pet").strip().lower()
        pet_kind = pet_type if pet_type in {"dog", "cat", "horse", "bird", "rabbit", "reptile"} else "other"
        noun = pet_kind if pet_kind != "other" else "pet"
        return {"kind": f"pet-{pet_kind}", "noun": noun, "label": noun}
    return {"kind": "namengine", "noun": "mark", "label": "NamEngine mark"}


def apply_taste_strength_inputs(brief, source) -> None:
    strengths: dict[str, int] = {}
    for key, value in source.items():
        if not str(key).startswith("taste_strength_"):
            continue
        try:
            strength = int(float(value))
        except (TypeError, ValueError):
            continue
        strength = max(0, min(100, strength))
        brief.inputs[str(key)] = strength
        strengths[str(key)[len("taste_strength_") :]] = strength

    if strengths:
        strongest = max(strengths.items(), key=lambda item: item[1])
        readable = strongest[0].replace("_", " ")
        brief.inputs["taste_focus"] = (
            f"Let {readable} guide this list most while still honoring every intake answer."
        )


def intake_edit_url(vertical, brief, field_id: str) -> str:
    query = {
        key: value
        for key, value in brief.inputs.items()
        if key not in {"species", "personality"}
        and not str(key).startswith("taste_")
        and value not in ("", None)
    }
    query["edit"] = field_id
    return f"{vertical.route_prefix}?{urlencode(query)}"


def feelings_scale_edit_url(vertical, brief) -> str:
    query = {
        key: value
        for key, value in brief.inputs.items()
        if key not in {"species", "personality", "taste_focus"} and value not in ("", None)
    }
    return f"{vertical.route_prefix}/feelings?{urlencode(query)}"


def display_brief_items(vertical, brief) -> list[dict[str, str]]:
    hidden_keys = {"species", "personality"}
    label_overrides = {
        "pet_type": "Pet",
        "pet_gender": "Gender",
        "pet_breed": "Breed",
        "pet_color": "Color",
        "pet_life_stage": "Age",
        "notes": "About them",
        "discovery_style": "Discovery",
        "style": "Style",
        "timeless_vs_distinctive": "Timeless vs distinctive",
        "familiarity_preference": "Familiarity",
        "pronunciation_importance": "Callability",
        "vibe": "Personality",
        "cultural_context": "Inspiration",
        "partner_alignment": "Torn between",
        "business_description": "Business",
        "industry": "Category",
        "stage": "Stage",
        "audience": "Audience",
        "name_shape": "Name shape",
        "domain_preference": "Domain priority",
        "product_description": "Product",
        "category": "Category",
        "sales_channel": "Sales channel",
    }

    items: list[dict[str, str]] = []
    for key, value in brief.inputs.items():
        if key in hidden_keys or str(key).startswith("taste_") or value in ("", None):
            continue
        label = label_overrides.get(key, key.replace("_", " ").title())
        items.append(
            {
                "key": key,
                "label": label,
                "value": str(value),
                "edit_url": intake_edit_url(vertical, brief, key),
            }
        )
    return items


def result_detail_from_session(session_id: str, result_id: str) -> dict | None:
    snapshot = get_session_snapshot(session_id)
    if snapshot is None:
        return None

    for row in snapshot["results"]:
        if row["id"] == result_id:
            reaction_values = _reaction_values(snapshot)
            available_results: list[dict] = []
            for chain_snapshot in get_session_chain_snapshots(session_id):
                available_results.extend(
                    json_loads(item["result_json"])
                    for item in chain_snapshot.get("results", [])
                )
            return {
                "session": snapshot["session"],
                "result": json_loads(row["result_json"]),
                "reaction_counts": snapshot["reaction_counts"],
                "taste_profile": _taste_profile_from_snapshot(snapshot),
                "reaction_value": reaction_values.get(result_id, ""),
                "available_results": available_results,
            }
    return None


def brief_query_string(brief_json: str) -> str:
    brief = json_loads(brief_json)
    inputs = {
        key: value
        for key, value in brief.get("inputs", {}).items()
        if value not in ("", None)
    }
    return urlencode(inputs)


def brief_value(brief_json: str, *keys: str) -> str:
    brief = json_loads(brief_json)
    inputs = brief.get("inputs", {})
    for key in keys:
        value = inputs.get(key)
        if value not in ("", None):
            return str(value)
    return ""


def make_session_id(vertical_slug: str, query_string: bytes) -> str:
    digest = sha1(vertical_slug.encode("utf-8") + b":" + query_string).hexdigest()
    return f"{vertical_slug}-{digest[:12]}"


def _query_string_from_mapping(source) -> str:
    return urlencode(
        {
            key: value
            for key, value in source.items()
            if value not in ("", None)
        }
    )


def _normalize_other_inputs(source) -> dict[str, str]:
    normalized = {
        key: value
        for key, value in source.items()
        if value not in ("", None) and not str(key).endswith("_other")
    }
    for key, value in source.items():
        if not str(key).endswith("_other"):
            continue
        base_key = str(key)[: -len("_other")]
        other_value = clip_text(value or "", OTHER_CHOICE_MAX_LENGTH)
        if other_value and normalized.get(base_key) == "Other":
            normalized[base_key] = other_value
    return normalized


def _sanitize_intake_source(vertical, source) -> dict[str, str]:
    """Keep only bounded intake values before caching, redirects, or AI prompts."""
    normalized = _normalize_other_inputs(source)
    sanitized: dict[str, str] = {}
    pet_legacy_aliases = {"species": "pet_type", "personality": "vibe"} if vertical.slug == "pet" else {}
    for question in vertical.intake_questions:
        raw_value = normalized.get(question.id, "")
        if raw_value in ("", None):
            legacy_key = next((old_key for old_key, new_key in pet_legacy_aliases.items() if new_key == question.id), "")
            raw_value = normalized.get(legacy_key, "") if legacy_key else ""
        value = clip_intake_value(question, raw_value)
        if value not in ("", None):
            sanitized[question.id] = value
    for key, value in normalized.items():
        key_text = str(key)
        if key_text.startswith("taste_strength_"):
            sanitized[key_text] = clip_text(value, 8)
    return sanitized


def _reaction_total(reaction_counts: dict[str, int]) -> int:
    return sum(int(reaction_counts.get(value, 0)) for value in ("love", "maybe", "no"))


def _reaction_counts_from_snapshot(snapshot: dict | None) -> dict[str, int]:
    counts = {"love": 0, "maybe": 0, "no": 0}
    for row in (snapshot or {}).get("reactions", []):
        value = str(row.get("value", ""))
        if value in counts:
            counts[value] += 1
    return counts


def _reaction_values(snapshot: dict | None) -> dict[str, str]:
    return {
        str(row["result_id"]): str(row["value"])
        for row in (snapshot or {}).get("reactions", [])
        if row.get("value") in {"love", "maybe", "no"}
    }


def _beta_access_secret() -> str:
    dedicated_secret = os.getenv("NAMENGINE_ACCESS_TOKEN_SECRET", "").strip()
    if dedicated_secret:
        return dedicated_secret
    return _LOCAL_BETA_ACCESS_SECRET


if not os.getenv("NAMENGINE_ACCESS_TOKEN_SECRET", "").strip():
    logger.warning(
        "NAMENGINE_ACCESS_TOKEN_SECRET is not set. Paid-access tokens will be signed with a "
        "random secret generated for this process only, which changes on every restart/deploy "
        "and will invalidate previously issued paid-access cookies. Set NAMENGINE_ACCESS_TOKEN_SECRET "
        "in the environment to a dedicated, stable secret to avoid this."
    )


def _signed_beta_access_token(vertical, return_session: str = "") -> str:
    issued_at = str(int(time.time()))
    payload = f"{vertical.slug}:{return_session}:{issued_at}"
    signature = hmac_new(
        _beta_access_secret().encode("utf-8"),
        payload.encode("utf-8"),
        sha1,
    ).hexdigest()
    return f"{return_session}:{issued_at}:{signature}"


def _valid_beta_access_token(vertical, token: str, *, max_age_seconds: int) -> bool:
    try:
        return_session, issued_at, signature = str(token or "").rsplit(":", 2)
        issued_at_int = int(issued_at)
    except (TypeError, ValueError):
        return False
    if issued_at_int <= 0 or int(time.time()) - issued_at_int > max_age_seconds:
        return False
    payload = f"{vertical.slug}:{return_session}:{issued_at}"
    expected = hmac_new(
        _beta_access_secret().encode("utf-8"),
        payload.encode("utf-8"),
        sha1,
    ).hexdigest()
    return compare_digest(signature, expected)


BETA_PAYMENT_LINK_DEFAULTS = {
    "business": "https://buy.stripe.com/test_aFa3cvchXg1E5CS2Yqds401",
    "pet": "https://buy.stripe.com/test_6oU5kD0zf4iW8P41Umds402",
    "baby": "https://buy.stripe.com/test_4gM5kDchX5n0aXc9mOds403",
}

LEGACY_BABY_PAYMENT_LINK = "https://buy.stripe.com/test_bJe5kDfu99Dg1mCdD4ds400"


def beta_pending_cookie_name(vertical) -> str:
    return f"namengine_access_checkout_{vertical.slug}"


def beta_unlock_cookie_name(vertical) -> str:
    return f"namengine_access_unlocked_{vertical.slug}"


def free_generation_cookie_name(vertical) -> str:
    return f"namengine_first_free_session_{vertical.slug}"


def beta_visitor_cookie_name() -> str:
    return BETA_VISITOR_COOKIE_NAME


def _beta_free_access_hours() -> int:
    try:
        return max(1, min(int(os.getenv("NAMENGINE_BETA_FREE_ACCESS_HOURS", BETA_FREE_ACCESS_HOURS_DEFAULT)), 24 * 30))
    except (TypeError, ValueError):
        return BETA_FREE_ACCESS_HOURS_DEFAULT


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _beta_visitor_id(create: bool = False) -> str:
    visitor_id = request.cookies.get(beta_visitor_cookie_name(), "").strip()
    if visitor_id:
        return visitor_id[:96]
    return token_urlsafe(24) if create else ""


CSRF_COOKIE_NAME = "namengine_csrf"


def csrf_token() -> str:
    """Return the current visitor's CSRF token, generating one if needed.

    Uses the double-submit cookie pattern: the token is a high-entropy random
    value (token_urlsafe(32), 256 bits) stored in a cookie. State-changing
    forms/requests must echo the same value back; a forged cross-site request
    cannot read the cookie (same-origin policy) so cannot supply a matching
    value. No server-side secret is required since the token itself has full
    cryptographic entropy -- unlike the paid-access tokens, this isn't signed
    against reuse across trust boundaries because there's nothing to sign;
    the raw random value is the whole security property.
    """
    existing = request.cookies.get(CSRF_COOKIE_NAME, "").strip()
    if existing:
        return existing
    if getattr(g, "csrf_token_to_set", None):
        return g.csrf_token_to_set
    token = token_urlsafe(32)
    g.csrf_token_to_set = token
    return token


def _valid_csrf_token(submitted) -> bool:
    cookie_value = request.cookies.get(CSRF_COOKIE_NAME, "").strip()
    submitted = str(submitted or "").strip()
    return bool(cookie_value) and compare_digest(cookie_value, submitted)


def _attach_beta_visitor_cookie(response, visitor_id: str):
    if visitor_id and request.cookies.get(beta_visitor_cookie_name()) != visitor_id:
        response.set_cookie(
            beta_visitor_cookie_name(),
            visitor_id,
            max_age=60 * 60 * 24 * 180,
            httponly=True,
            samesite="Lax",
            secure=request.is_secure,
        )
    return response


def _email_capture_value() -> str:
    email = " ".join(str(request.form.get("email", "")).strip().split())
    return email[:BETA_EMAIL_MAX_LENGTH]


def _valid_email_capture(email: str) -> bool:
    return bool(email and len(email) <= BETA_EMAIL_MAX_LENGTH and BETA_EMAIL_PATTERN.match(email))


def _vertical_from_request():
    requested_slug = request.path.strip("/").split("/", 1)[0]
    if requested_slug in VERTICALS:
        return get_vertical(requested_slug)
    route_session_id = (request.view_args or {}).get("session_id", "")
    session_id = str(
        route_session_id
        or request.form.get("session_id", "")
        or request.args.get("session_id", "")
    )
    for slug in VERTICALS:
        if session_id.startswith(f"{slug}-"):
            return get_vertical(slug)
    return None


def beta_unlocked_from_request(vertical=None) -> bool:
    """Return whether this request has a long-lived server-issued paid-access unlock."""
    vertical = vertical or _vertical_from_request()
    if vertical is None:
        return False
    access_token = request.cookies.get(beta_unlock_cookie_name(vertical), "")
    return _valid_beta_access_token(vertical, access_token, max_age_seconds=60 * 60 * 24 * 30)


def beta_pending_checkout_from_request(vertical=None) -> bool:
    """Return whether this request is returning from a verified Stripe checkout."""
    vertical = vertical or _vertical_from_request()
    if vertical is None:
        return False
    if not _valid_beta_access_token(
        vertical,
        request.cookies.get(beta_pending_cookie_name(vertical), ""),
        max_age_seconds=60 * 60 * 6,
    ):
        return False
    return _stripe_checkout_session_paid(beta_stripe_checkout_session_id_from_request(), vertical)


def beta_payment_link_for(vertical) -> str:
    """Return the canonical vertical-specific Stripe Payment Link."""
    key = f"NAMENGINE_{vertical.slug.upper()}_BETA_PAYMENT_LINK"
    configured_link = os.getenv(key, "").strip()
    default_link = BETA_PAYMENT_LINK_DEFAULTS.get(vertical.slug, "")
    payment_link = configured_link or default_link
    if payment_link == LEGACY_BABY_PAYMENT_LINK:
        return default_link
    return payment_link


def _payment_link_id_from_value(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("plink_"):
        return value
    parsed_path = urlparse(value).path.strip("/")
    for part in parsed_path.split("/"):
        if part.startswith("plink_"):
            return part
    return ""


def beta_payment_link_id_for(vertical) -> str:
    """Return a configured Stripe Payment Link id, if available."""
    slug = vertical.slug.upper()
    for key in (
        f"NAMENGINE_{slug}_STRIPE_PAYMENT_LINK_ID",
        f"NAMENGINE_{slug}_BETA_PAYMENT_LINK_ID",
        "NAMENGINE_STRIPE_PAYMENT_LINK_ID",
    ):
        value = _payment_link_id_from_value(os.getenv(key, ""))
        if value:
            return value
    return _payment_link_id_from_value(beta_payment_link_for(vertical))


def _stripe_secret_key() -> str:
    return (
        os.getenv("STRIPE_SECRET_KEY", "").strip()
        or os.getenv("NAMENGINE_STRIPE_SECRET_KEY", "").strip()
    )


def _format_stripe_price(unit_amount: int | None, currency: str | None) -> str:
    if unit_amount is None:
        return ""
    currency = str(currency or "usd").upper()
    major = unit_amount / 100
    if currency == "USD":
        return f"${major:,.2f}"
    return f"{major:,.2f} {currency}"


_STRIPE_PRICE_CACHE: dict[str, tuple[float, str]] = {}
_STRIPE_LINK_ID_CACHE: dict[str, tuple[float, str]] = {}
_STRIPE_PRICE_ID_CACHE: dict[str, tuple[float, str]] = {}
_STRIPE_PRICE_CACHE_LOCK = Lock()
_STRIPE_PRICE_CACHE_SECONDS = 15 * 60


def _stripe_auth_header(secret_key: str) -> str:
    auth = b64encode(f"{secret_key}:".encode("utf-8")).decode("ascii")
    return f"Basic {auth}"


def _stripe_api_get(path: str, secret_key: str) -> dict:
    request = Request(
        f"https://api.stripe.com/v1/{path.lstrip('/')}",
        headers={"Authorization": _stripe_auth_header(secret_key)},
    )
    with urlopen(request, timeout=8) as response:
        return json_loads(response.read().decode("utf-8"))


def _stripe_api_post(path: str, secret_key: str, data: dict[str, str]) -> dict:
    encoded = urlencode(data).encode("utf-8")
    request = Request(
        f"https://api.stripe.com/v1/{path.lstrip('/')}",
        data=encoded,
        headers={
            "Authorization": _stripe_auth_header(secret_key),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urlopen(request, timeout=8) as response:
        return json_loads(response.read().decode("utf-8"))


def _stripe_payment_link_id_from_url(payment_link_url: str, secret_key: str) -> str:
    payment_link_url = str(payment_link_url or "").strip()
    if not payment_link_url or not secret_key:
        return ""

    now = time.time()
    with _STRIPE_PRICE_CACHE_LOCK:
        cached = _STRIPE_LINK_ID_CACHE.get(payment_link_url)
        if cached and now - cached[0] < _STRIPE_PRICE_CACHE_SECONDS:
            return cached[1]

    try:
        payload = _stripe_api_get("payment_links?limit=100", secret_key)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("Could not list Stripe payment links: %s", exc.__class__.__name__)
        return ""

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return ""
    for item in data:
        if not isinstance(item, dict):
            continue
        if str(item.get("url") or "").strip() == payment_link_url:
            payment_link_id = str(item.get("id") or "").strip()
            if payment_link_id:
                with _STRIPE_PRICE_CACHE_LOCK:
                    _STRIPE_LINK_ID_CACHE[payment_link_url] = (now, payment_link_id)
                return payment_link_id
    return ""


def _stripe_payment_link_price(payment_link_id: str, secret_key: str) -> str:
    """Read the first active line-item price from Stripe for a Payment Link."""
    payment_link_id = str(payment_link_id or "").strip()
    if not payment_link_id or not secret_key:
        return ""

    now = time.time()
    with _STRIPE_PRICE_CACHE_LOCK:
        cached = _STRIPE_PRICE_CACHE.get(payment_link_id)
        if cached and now - cached[0] < _STRIPE_PRICE_CACHE_SECONDS:
            return cached[1]

    try:
        payload = _stripe_api_get(f"payment_links/{payment_link_id}/line_items?limit=1", secret_key)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("Could not load Stripe price for %s: %s", payment_link_id, exc.__class__.__name__)
        return ""

    data = payload.get("data") if isinstance(payload, dict) else None
    item = data[0] if isinstance(data, list) and data else {}
    price = item.get("price") if isinstance(item, dict) else {}
    if not isinstance(price, dict):
        return ""
    display_price = _format_stripe_price(price.get("unit_amount"), price.get("currency"))
    if display_price:
        with _STRIPE_PRICE_CACHE_LOCK:
            _STRIPE_PRICE_CACHE[payment_link_id] = (now, display_price)
    return display_price


def _stripe_price_id_from_payment_link(payment_link_id: str, secret_key: str) -> str:
    """Read the first active line-item price id from a Stripe Payment Link."""
    payment_link_id = str(payment_link_id or "").strip()
    if not payment_link_id or not secret_key:
        return ""

    now = time.time()
    with _STRIPE_PRICE_CACHE_LOCK:
        cached = _STRIPE_PRICE_ID_CACHE.get(payment_link_id)
        if cached and now - cached[0] < _STRIPE_PRICE_CACHE_SECONDS:
            return cached[1]

    try:
        payload = _stripe_api_get(f"payment_links/{payment_link_id}/line_items?limit=1", secret_key)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("Could not load Stripe price id for %s: %s", payment_link_id, exc.__class__.__name__)
        return ""

    data = payload.get("data") if isinstance(payload, dict) else None
    item = data[0] if isinstance(data, list) and data else {}
    price = item.get("price") if isinstance(item, dict) else {}
    price_id = str(price.get("id") or "").strip() if isinstance(price, dict) else ""
    if price_id:
        with _STRIPE_PRICE_CACHE_LOCK:
            _STRIPE_PRICE_ID_CACHE[payment_link_id] = (now, price_id)
    return price_id


def beta_stripe_price_id_for(vertical) -> str:
    slug = vertical.slug.upper()
    for key in (
        f"NAMENGINE_{slug}_STRIPE_PRICE_ID",
        f"NAMENGINE_{slug}_BETA_PRICE_ID",
        "NAMENGINE_STRIPE_PRICE_ID",
    ):
        value = os.getenv(key, "").strip()
        if value.startswith("price_"):
            return value
    secret_key = _stripe_secret_key()
    payment_link_id = beta_payment_link_id_for(vertical)
    if not payment_link_id:
        payment_link_id = _stripe_payment_link_id_from_url(beta_payment_link_for(vertical), secret_key)
    return _stripe_price_id_from_payment_link(payment_link_id, secret_key)


def _absolute_url(path: str) -> str:
    return urljoin(request.url_root, path.lstrip("/"))


def _stripe_checkout_success_url(vertical, return_session: str) -> str:
    query = "checkout_session_id={CHECKOUT_SESSION_ID}"
    if return_session:
        query = f"{query}&{urlencode({'return_session': return_session})}"
    return _absolute_url(f"{url_for('beta_landing', vertical_slug=vertical.slug)}?{query}")


def _stripe_checkout_cancel_url(vertical, return_session: str) -> str:
    access_path = url_for("beta_landing", vertical_slug=vertical.slug)
    if return_session:
        access_path = f"{access_path}?{urlencode({'return_session': return_session})}"
    return _absolute_url(access_path)


def _stripe_payment_link_checkout_url(payment_link: str, return_session: str) -> str:
    payment_link = str(payment_link or "").strip()
    return_session = str(return_session or "").strip()
    if not payment_link or not return_session:
        return payment_link
    separator = "&" if "?" in payment_link else "?"
    return f"{payment_link}{separator}{urlencode({'client_reference_id': return_session})}"


def _create_stripe_checkout_session(vertical, return_session: str) -> str:
    """Create a Stripe Checkout Session with an app-controlled success URL."""
    secret_key = _stripe_secret_key()
    price_id = beta_stripe_price_id_for(vertical)
    if not secret_key or not price_id:
        return ""
    data = {
        "mode": "payment",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "success_url": _stripe_checkout_success_url(vertical, return_session),
        "cancel_url": _stripe_checkout_cancel_url(vertical, return_session),
        "client_reference_id": return_session or vertical.slug,
        "metadata[namengine_vertical]": vertical.slug,
        "metadata[namengine_access]": "1",
        "metadata[namengine_return_session]": return_session,
    }
    try:
        payload = _stripe_api_post("checkout/sessions", secret_key, data)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("Could not create Stripe checkout session for %s: %s", vertical.slug, exc.__class__.__name__)
        return ""
    if not isinstance(payload, dict):
        return ""
    checkout_url = str(payload.get("url") or "").strip()
    return checkout_url if checkout_url.startswith("https://") else ""


def _stripe_checkout_session_paid(session_id: str, vertical) -> bool:
    """Verify a Stripe Checkout Session before granting paid access."""
    session_id = str(session_id or "").strip()
    secret_key = _stripe_secret_key()
    if not session_id or not secret_key:
        return False
    try:
        payload = _stripe_api_get(f"checkout/sessions/{session_id}", secret_key)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("Could not verify Stripe checkout session %s: %s", session_id, exc.__class__.__name__)
        return False
    if not isinstance(payload, dict):
        return False
    if payload.get("payment_status") != "paid" or payload.get("status") != "complete":
        return False
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if (
        metadata.get("namengine_access") == "1"
        and metadata.get("namengine_vertical") == vertical.slug
    ):
        return True
    payment_link_id = beta_payment_link_id_for(vertical) or _stripe_payment_link_id_from_url(
        beta_payment_link_for(vertical),
        secret_key,
    )
    session_payment_link = str(payload.get("payment_link") or "").strip()
    return bool(payment_link_id) and session_payment_link == payment_link_id


def _checkout_return_session_candidate(vertical, value: str) -> str:
    session_id = str(value or "").strip()
    if session_id and session_id.startswith(f"{vertical.slug}-"):
        return session_id
    return ""


def _beta_return_session_from_signed_cookie(vertical, cookie_name: str, *, max_age_seconds: int) -> str:
    token = request.cookies.get(cookie_name, "")
    if not _valid_beta_access_token(vertical, token, max_age_seconds=max_age_seconds):
        return ""
    try:
        return_session, _issued_at, _signature = str(token or "").rsplit(":", 2)
    except (TypeError, ValueError):
        return ""
    return _checkout_return_session_candidate(vertical, return_session)


def _beta_pending_return_session_from_request(vertical) -> str:
    """Recover the original results session from the signed checkout-continuity cookie."""
    return _beta_return_session_from_signed_cookie(
        vertical,
        beta_pending_cookie_name(vertical),
        max_age_seconds=60 * 60 * 6,
    )


def _beta_unlocked_return_session_from_request(vertical) -> str:
    """Recover the paid user's original results session from the long-lived unlock cookie."""
    return _beta_return_session_from_signed_cookie(
        vertical,
        beta_unlock_cookie_name(vertical),
        max_age_seconds=60 * 60 * 24 * 30,
    )


def _stripe_checkout_return_session(session_id: str, vertical) -> str:
    """Recover the app-created Checkout Session's original results session from Stripe metadata."""
    session_id = str(session_id or "").strip()
    secret_key = _stripe_secret_key()
    if not session_id or not secret_key:
        return ""
    try:
        payload = _stripe_api_get(f"checkout/sessions/{session_id}", secret_key)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("Could not recover Stripe checkout return session %s: %s", session_id, exc.__class__.__name__)
        return ""
    if not isinstance(payload, dict):
        return ""
    if payload.get("payment_status") != "paid" or payload.get("status") != "complete":
        return ""
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if metadata.get("namengine_access") == "1" and metadata.get("namengine_vertical") == vertical.slug:
        return _checkout_return_session_candidate(
            vertical,
            str(metadata.get("namengine_return_session") or payload.get("client_reference_id") or ""),
        )
    payment_link_id = beta_payment_link_id_for(vertical) or _stripe_payment_link_id_from_url(
        beta_payment_link_for(vertical),
        secret_key,
    )
    session_payment_link = str(payload.get("payment_link") or "").strip()
    if payment_link_id and session_payment_link == payment_link_id:
        return _checkout_return_session_candidate(vertical, str(payload.get("client_reference_id") or ""))
    return ""


def _stripe_checkout_return_session_from_request(vertical) -> str:
    return _stripe_checkout_return_session(beta_stripe_checkout_session_id_from_request(), vertical)


def beta_stripe_checkout_session_id_from_request() -> str:
    return (
        request.args.get("checkout_session_id", "").strip()
        or request.args.get("session_id", "").strip()
    )


def beta_price_for(vertical) -> str:
    """Return the Stripe-backed vertical access price display."""
    secret_key = _stripe_secret_key()
    payment_link_id = beta_payment_link_id_for(vertical)
    if not payment_link_id:
        payment_link_id = _stripe_payment_link_id_from_url(beta_payment_link_for(vertical), secret_key)
    stripe_price = _stripe_payment_link_price(payment_link_id, secret_key)
    if stripe_price:
        return stripe_price
    return "$9.99"


def beta_cta_label(vertical) -> str:
    return f"Unlock {vertical.display_name} Access"


def beta_unlock_error(vertical) -> str:
    return f"Unlock {vertical.display_name} access to explore, react, compare, choose, share, and generate refined lists."


def _access_required_response(vertical, session_id: str, *, wants_json: bool = False):
    access_url = url_for("beta_landing", vertical_slug=vertical.slug, return_session=session_id)
    message = beta_unlock_error(vertical)
    if wants_json:
        return jsonify({"error": "access_required", "message": message, "access_url": access_url}), 402
    return redirect(access_url)


def _free_generation_access_required_response(vertical, session_id: str):
    return _access_required_response(vertical, session_id)


def _beta_usage_expired(usage: dict | None) -> bool:
    if not usage:
        return False
    expires_at = _parse_iso_datetime(str(usage.get("free_access_expires_at") or ""))
    return expires_at is not None and expires_at <= _utcnow()


def _free_session_access_blocked(vertical, session_id: str) -> bool:
    """Return whether a free visitor can no longer view this cached free session."""
    if beta_unlocked_from_request(vertical):
        return False

    visitor_id = _beta_visitor_id(create=False)

    if visitor_id:
        usage = get_beta_usage(visitor_id, vertical.slug)
        if usage:
            if str(usage.get("free_session_id") or "") != session_id:
                return True
            return _beta_usage_expired(usage)

    # Old pre-ledger browsers (no visitor ledger yet): allow access.
    # _remember_free_generation will create their visitor ledger entry.
    # Permanently blocking them via old cookie was too aggressive.
    return False


def _free_generation_blocked(vertical, session_id: str, *, needs_generation: bool) -> bool:
    """Allow one free generated list per vertical/browser, then require paid access for new lists."""
    if not needs_generation or beta_unlocked_from_request(vertical):
        return False

    visitor_id = _beta_visitor_id(create=False)
    if visitor_id:
        usage = get_beta_usage(visitor_id, vertical.slug)
        if usage:
            return str(usage.get("free_session_id") or "") != session_id or _beta_usage_expired(usage)

    # Old pre-ledger browsers (no visitor ledger yet): allow generation.
    # _remember_free_generation will create their visitor ledger entry going forward.
    return False


def _remember_free_generation(response, vertical, session_id: str):
    if beta_unlocked_from_request(vertical):
        return response
    visitor_id = _beta_visitor_id(create=True)
    now = _utcnow()
    expires_at = now + timedelta(hours=_beta_free_access_hours())
    save_beta_usage_free_session(
        visitor_id=visitor_id,
        vertical=vertical.slug,
        session_id=session_id,
        first_free_at=_isoformat(now),
        free_access_expires_at=_isoformat(expires_at),
    )
    _attach_beta_visitor_cookie(response, visitor_id)
    if request.cookies.get(free_generation_cookie_name(vertical)):
        return response
    response.set_cookie(
        free_generation_cookie_name(vertical),
        session_id,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure,
    )
    return response


def beta_return_cookie_name(vertical) -> str:
    return f"namengine_access_return_{vertical.slug}"


def beta_return_session_for(vertical) -> str:
    return_session = (
        request.args.get("return_session", "").strip()
        or request.cookies.get(beta_return_cookie_name(vertical), "").strip()
    )
    if return_session and not return_session.startswith(f"{vertical.slug}-"):
        return ""
    return return_session


def _beta_usage_session_id(vertical, beta_usage: dict | None) -> str:
    session_id = str((beta_usage or {}).get("free_session_id") or "").strip()
    if session_id and session_id.startswith(f"{vertical.slug}-"):
        return session_id
    return ""


def _beta_paid_continue_url(vertical, return_session: str, beta_usage: dict | None) -> str:
    session_id = return_session or _beta_usage_session_id(vertical, beta_usage)
    if session_id:
        return url_for("session_results", session_id=session_id)
    return url_for("intake", vertical_slug=vertical.slug)


def _brief_from_snapshot(snapshot: dict) -> NamingBrief:
    return NamingBrief(**json_loads(snapshot["session"]["brief_json"]))


def _render_results_snapshot(
    session_id: str,
    *,
    status: int = 200,
    refinement_error: str | None = None,
):
    snapshot = get_session_snapshot(session_id)
    if snapshot is None:
        abort(404)

    vertical = get_vertical(snapshot["session"]["vertical"])
    if status == 200 and _free_session_access_blocked(vertical, session_id):
        return _free_generation_access_required_response(vertical, session_id)

    names = _names_from_snapshot(snapshot)
    brief = _brief_from_snapshot(snapshot)
    if not _cached_names_match_current_rules(vertical, brief, names):
        if _free_generation_blocked(vertical, session_id, needs_generation=True):
            return _free_generation_access_required_response(vertical, session_id)
        names = _generate_names_for_route(vertical, brief)
        save_session(
            session_id,
            vertical.slug,
            brief,
            names,
            round_number=int(snapshot["session"]["round_number"]),
            parent_session_id=snapshot["session"].get("parent_session_id"),
            refinement_prompt=snapshot["session"].get("refinement_prompt"),
        )
        snapshot = get_session_snapshot(session_id) or snapshot
    reaction_counts = snapshot.get("reaction_counts") or _reaction_counts_from_snapshot(snapshot)
    response = make_response(
        render_template(
            "results.html",
            vertical=vertical,
            brief=brief,
            names=names,
            trust_cue=build_trust_cue(names),
            session_id=session_id,
            reaction_counts=reaction_counts,
            reaction_values=_reaction_values(snapshot),
            reaction_total=_reaction_total(reaction_counts),
            min_reactions_for_refinement=MIN_REACTIONS_FOR_REFINEMENT,
            taste_profile=_taste_profile_from_snapshot(snapshot),
            round_number=int(snapshot["session"]["round_number"]),
            parent_session_id=snapshot["session"]["parent_session_id"],
            original_mode=session_id.startswith("pet-original"),
            refinement_error=refinement_error,
            beta_unlocked=beta_unlocked_from_request(vertical),
        ),
        status,
    )
    return _remember_free_generation(response, vertical, session_id)


def save_feedback_submission(source) -> None:
    import json

    feedback_path = get_database_path().parent / "feedback.jsonl"
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    allowed_keys = (
        "name",
        "tester_type",
        "overall_rating",
        "liked_most",
        "confusing",
        "missing",
    )
    payload = {
        key: str(source.get(key, "")).strip()
        for key in allowed_keys
        if str(source.get(key, "")).strip()
    }
    if not payload:
        return
    with feedback_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def create_app() -> Flask:
    if load_dotenv is not None:
        load_dotenv()
    app = Flask(__name__)

    @app.errorhandler(NameGenerationUnavailable)
    def generation_unavailable(exc: NameGenerationUnavailable):
        requested_slug = request.path.strip("/").split("/", 1)[0]
        error_vertical = get_vertical(requested_slug) if requested_slug in VERTICALS else None
        return (
            render_template(
                "generation_unavailable.html",
                message=str(exc) or "We could not generate names right now.",
                vertical=error_vertical,
            ),
            503,
        )

    @app.context_processor
    def inject_platform_context():
        return {
            "contract_version": CONTRACT_VERSION,
            "verticals": VERTICALS,
            "vertical_theme_style": vertical_theme_style,
            "grouped_questions": grouped_questions,
            "display_brief_items": display_brief_items,
            "intake_edit_url": intake_edit_url,
            "feelings_scale_edit_url": feelings_scale_edit_url,
            "feelings_scale_enabled": feelings_scale_enabled,
            "feeling_section_titles": feeling_section_titles,
            "section_strength_field": section_strength_field,
            "feeling_center_icon": feeling_center_icon,
            "meaningful_card_text": meaningful_card_text,
            "compact_card_text": compact_card_text,
            "collapsed_result_meaning": collapsed_result_meaning,
            "intake_field_max_length": intake_field_max_length,
            "other_choice_max_length": OTHER_CHOICE_MAX_LENGTH,
            "refinement_instruction_max_length": REFINEMENT_INSTRUCTION_MAX_LENGTH,
            "beta_unlocked_from_request": beta_unlocked_from_request,
            "beta_cta_label": beta_cta_label,
            "csrf_token": csrf_token,
        }

    @app.after_request
    def _attach_pending_csrf_cookie(response):
        token = getattr(g, "csrf_token_to_set", None)
        if token:
            response.set_cookie(
                CSRF_COOKIE_NAME,
                token,
                max_age=60 * 60 * 24 * 180,
                httponly=False,
                samesite="Lax",
                secure=request.is_secure,
            )
        return response

    app.add_template_filter(brief_query_string, "brief_query_string")
    app.add_template_filter(brief_value, "brief_value")
    app.add_template_filter(_safe_audit_value, "safe_audit")

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            verticals=VERTICALS,
            beta_price=beta_price_for(get_vertical("baby")),
        )

    @app.get("/<vertical_slug>/beta")
    @app.get("/<vertical_slug>/access")
    def beta_landing(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)
        vertical = get_vertical(vertical_slug)
        visitor_id = _beta_visitor_id(create=True)
        return_session = beta_return_session_for(vertical)
        paid = beta_unlocked_from_request(vertical)
        if paid and not return_session:
            return_session = _beta_unlocked_return_session_from_request(vertical)
        checkout_session_id = beta_stripe_checkout_session_id_from_request()
        checkout_return = beta_pending_checkout_from_request(vertical)
        if checkout_session_id and not checkout_return:
            checkout_return = _stripe_checkout_session_paid(checkout_session_id, vertical)
        if checkout_return and not return_session:
            return_session = (
                _beta_pending_return_session_from_request(vertical)
                or _stripe_checkout_return_session_from_request(vertical)
            )
        stripe_payment_link = beta_payment_link_for(vertical)
        beta_usage = get_beta_usage(visitor_id, vertical.slug) if visitor_id else None
        paid_session_id = return_session or _beta_usage_session_id(vertical, beta_usage)
        checkout_return_session = return_session or _beta_usage_session_id(vertical, beta_usage)
        beta_checkout_url = (
            url_for("beta_checkout", vertical_slug=vertical.slug, return_session=checkout_return_session)
            if stripe_payment_link
            else ""
        )
        beta_continue_url = _beta_paid_continue_url(vertical, return_session, beta_usage)
        if (paid or checkout_return) and paid_session_id:
            if get_session_snapshot(paid_session_id) is not None:
                response = redirect(url_for("session_results", session_id=paid_session_id))
            else:
                # Session no longer exists (e.g. expired, different device).
                # Fall back to intake rather than letting session_results abort(404).
                response = redirect(url_for("intake", vertical_slug=vertical.slug))
        else:
            response = make_response(
                render_template(
                    "baby_beta.html",
                    vertical=vertical,
                    stripe_payment_link=stripe_payment_link,
                    beta_checkout_url=beta_checkout_url,
                    beta_price=beta_price_for(vertical),
                    paid=paid or checkout_return,
                    beta_return_session=return_session if paid else "",
                    beta_has_prior_round=bool(paid_session_id),
                    beta_continue_url=beta_continue_url,
                    focused_access_return=bool(return_session) and not (paid or checkout_return),
                    beta_usage=beta_usage,
                    beta_email_captured=bool((beta_usage or {}).get("email")),
                    beta_email_capture_url=url_for("beta_email_capture", vertical_slug=vertical.slug),
                    beta_email_return_session=return_session,
                )
            )
        _attach_beta_visitor_cookie(response, visitor_id)
        if checkout_return:
            response.set_cookie(
                beta_unlock_cookie_name(vertical),
                _signed_beta_access_token(vertical, paid_session_id),
                max_age=60 * 60 * 24 * 30,
                httponly=True,
                samesite="Lax",
                secure=request.is_secure,
            )
            response.delete_cookie(beta_pending_cookie_name(vertical))
        if (paid or checkout_return) and paid_session_id:
            response.delete_cookie(beta_return_cookie_name(vertical))
        return response

    @app.post("/<vertical_slug>/access/email")
    def beta_email_capture(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)
        vertical = get_vertical(vertical_slug)
        visitor_id = _beta_visitor_id(create=True)
        return_session = str(request.form.get("return_session", "")).strip() or beta_return_session_for(vertical)
        if return_session and not return_session.startswith(f"{vertical.slug}-"):
            return_session = ""
        email = _email_capture_value()
        if not _valid_email_capture(email):
            response = make_response(
                render_template(
                    "baby_beta.html",
                    vertical=vertical,
                    stripe_payment_link=beta_payment_link_for(vertical),
                    beta_checkout_url=url_for("beta_checkout", vertical_slug=vertical.slug, return_session=return_session),
                    beta_price=beta_price_for(vertical),
                    paid=False,
                    beta_return_session="",
                    beta_has_prior_round=bool(return_session),
                    beta_continue_url=url_for("intake", vertical_slug=vertical.slug),
                    focused_access_return=bool(return_session),
                    beta_usage=get_beta_usage(visitor_id, vertical.slug) if visitor_id else None,
                    beta_email_captured=False,
                    beta_email_capture_url=url_for("beta_email_capture", vertical_slug=vertical.slug),
                    beta_email_return_session=return_session,
                    beta_email_error="Enter a valid email address.",
                ),
                400,
            )
            return _attach_beta_visitor_cookie(response, visitor_id)

        save_beta_email_capture(
            visitor_id=visitor_id,
            vertical=vertical.slug,
            email=email,
            return_session=return_session,
        )
        save_beta_usage_email(visitor_id=visitor_id, vertical=vertical.slug, email=email)
        response = redirect(url_for("beta_landing", vertical_slug=vertical.slug, return_session=return_session, email_saved="1"))
        return _attach_beta_visitor_cookie(response, visitor_id)

    @app.get("/<vertical_slug>/beta/checkout")
    @app.get("/<vertical_slug>/access/checkout")
    def beta_checkout(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)
        vertical = get_vertical(vertical_slug)
        return_session = request.args.get("return_session", "").strip() or beta_return_session_for(vertical)
        if return_session and not return_session.startswith(f"{vertical.slug}-"):
            return_session = ""
        if not return_session:
            visitor_id = _beta_visitor_id(create=False)
            beta_usage = get_beta_usage(visitor_id, vertical.slug) if visitor_id else None
            return_session = _beta_usage_session_id(vertical, beta_usage)
        stripe_payment_link = beta_payment_link_for(vertical)
        if not stripe_payment_link:
            return redirect(url_for("beta_landing", vertical_slug=vertical.slug))
        checkout_url = _create_stripe_checkout_session(vertical, return_session) or _stripe_payment_link_checkout_url(
            stripe_payment_link,
            return_session,
        )
        response = redirect(checkout_url)
        response.set_cookie(
            beta_pending_cookie_name(vertical),
            _signed_beta_access_token(vertical, return_session),
            max_age=60 * 60 * 6,
            httponly=True,
            samesite="Lax",
            secure=request.is_secure,
        )
        if return_session:
            response.set_cookie(
                beta_return_cookie_name(vertical),
                return_session,
                max_age=60 * 60,
                httponly=True,
                samesite="Lax",
                secure=request.is_secure,
            )
        return response

    @app.get("/about")
    def about():
        return render_template("about.html")

    @app.get("/privacy")
    def privacy_policy():
        return render_template("legal_privacy.html")

    @app.get("/terms")
    def terms_of_use():
        return render_template("legal_terms.html")

    @app.get("/disclaimers")
    def disclaimers():
        return render_template("legal_disclaimers.html")

    @app.get("/data-protection")
    def data_protection():
        return render_template("legal_data_protection.html")

    @app.get("/<vertical_slug>")
    def intake(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        vertical = get_vertical(vertical_slug)
        return render_template(
            "intake.html",
            vertical=vertical,
            beta_unlocked=beta_unlocked_from_request(vertical),
        )


    @app.get("/<vertical_slug>/feelings")
    def feelings_scale(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        vertical = get_vertical(vertical_slug)
        if not feelings_scale_enabled(vertical):
            query = _query_string_from_mapping(_sanitize_intake_source(vertical, request.args.to_dict(flat=True)))
            return redirect(f"{vertical.route_prefix}/results?{query}")

        source = _sanitize_intake_source(vertical, request.args.to_dict(flat=True))
        brief = build_brief(vertical, source)
        return render_template(
            "feelings_scale.html",
            vertical=vertical,
            brief=brief,
            source=source,
            sections=feeling_section_titles(vertical),
            center_icon=feeling_center_icon(vertical, source),
            beta_unlocked=beta_unlocked_from_request(vertical),
        )

    @app.get("/pet/original")
    def pet_original():
        vertical = get_vertical("pet")
        return render_template("original_intake.html", vertical=vertical)

    @app.post("/pet/original/results")
    def pet_original_submit():
        vertical = get_vertical("pet")
        query = _query_string_from_mapping(_sanitize_intake_source(vertical, request.form))
        return redirect(f"{url_for('pet_original_results')}?{query}")

    @app.get("/pet/original/results")
    def pet_original_results():
        vertical = get_vertical("pet")
        source_for_id = _sanitize_intake_source(vertical, request.args.to_dict(flat=True))
        source = dict(source_for_id)
        source["discovery_style"] = source.get("discovery_style") or "Completely original"
        source["original_mode"] = "true"
        brief = build_brief(vertical, source)
        apply_taste_strength_inputs(brief, source)
        for key in ("starting_letter", "length_preference", "avoid_feel", "original_mode"):
            if source.get(key):
                brief.inputs[key] = source[key]
        session_id = make_session_id("pet-original", _query_string_from_mapping(source_for_id).encode("utf-8"))
        snapshot = get_session_snapshot(session_id)
        if snapshot and snapshot["results"]:
            names = _names_from_snapshot(snapshot)
        else:
            if _free_generation_blocked(vertical, session_id, needs_generation=True):
                return _free_generation_access_required_response(vertical, session_id)
            names = _generate_names_for_route(vertical, brief)
            save_session(session_id, vertical.slug, brief, names)
            snapshot = get_session_snapshot(session_id)
        reaction_counts = snapshot.get("reaction_counts") if snapshot else {"love": 0, "maybe": 0, "no": 0}
        response = make_response(render_template(
            "results.html",
            vertical=vertical,
            brief=brief,
            names=names,
            trust_cue=build_trust_cue(names),
            session_id=session_id,
            reaction_counts=reaction_counts,
            reaction_values=_reaction_values(snapshot),
            taste_profile=_taste_profile_from_snapshot(snapshot or {}),
            round_number=1,
            parent_session_id=None,
            original_mode=True,
            beta_unlocked=beta_unlocked_from_request(vertical),
        ))
        return _remember_free_generation(response, vertical, session_id)

    def _create_results_session(vertical, source: dict[str, str]) -> str:
        source = _sanitize_intake_source(vertical, source)
        brief = build_brief(vertical, source)
        apply_taste_strength_inputs(brief, source)

        session_id = make_session_id(
            vertical.slug,
            _query_string_from_mapping(source).encode("utf-8"),
        )
        snapshot = get_session_snapshot(session_id)
        if snapshot and snapshot["results"]:
            names = _names_from_snapshot(snapshot)
            if not _cached_names_match_current_rules(vertical, brief, names):
                if _free_generation_blocked(vertical, session_id, needs_generation=True):
                    raise FreeGenerationAccessRequired(session_id)
                names = _generate_names_for_route(vertical, brief)
                save_session(session_id, vertical.slug, brief, names)
        else:
            if _free_generation_blocked(vertical, session_id, needs_generation=True):
                raise FreeGenerationAccessRequired(session_id)
            names = _generate_names_for_route(vertical, brief)
            save_session(session_id, vertical.slug, brief, names)
        return session_id

    @app.post("/<vertical_slug>/results")
    def submit_results(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        vertical = get_vertical(vertical_slug)
        try:
            session_id = _create_results_session(vertical, request.form.to_dict(flat=True))
        except FreeGenerationAccessRequired as exc:
            return _free_generation_access_required_response(vertical, exc.session_id)
        response = redirect(url_for("session_results", session_id=session_id))
        return _remember_free_generation(response, vertical, session_id)

    @app.get("/<vertical_slug>/results")
    def results(vertical_slug: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        vertical = get_vertical(vertical_slug)
        source = _sanitize_intake_source(vertical, request.args.to_dict(flat=True))
        brief = build_brief(vertical, source)
        apply_taste_strength_inputs(brief, source)

        session_id = make_session_id(vertical.slug, _query_string_from_mapping(source).encode("utf-8"))
        snapshot = get_session_snapshot(session_id)
        if snapshot and snapshot["results"]:
            if _free_session_access_blocked(vertical, session_id):
                return _free_generation_access_required_response(vertical, session_id)
            names = _names_from_snapshot(snapshot)
            if not _cached_names_match_current_rules(vertical, brief, names):
                if _free_generation_blocked(vertical, session_id, needs_generation=True):
                    return _free_generation_access_required_response(vertical, session_id)
                names = _generate_names_for_route(vertical, brief)
                save_session(session_id, vertical.slug, brief, names)
        else:
            if _free_generation_blocked(vertical, session_id, needs_generation=True):
                return _free_generation_access_required_response(vertical, session_id)
            names = _generate_names_for_route(vertical, brief)
            save_session(session_id, vertical.slug, brief, names)
            snapshot = get_session_snapshot(session_id)
        reaction_counts = snapshot.get("reaction_counts") if snapshot else {"love": 0, "maybe": 0, "no": 0}
        response = make_response(render_template(
            "results.html",
            vertical=vertical,
            brief=brief,
            names=names,
            trust_cue=build_trust_cue(names),
            session_id=session_id,
            reaction_counts=reaction_counts,
            reaction_values=_reaction_values(snapshot),
            taste_profile=_taste_profile_from_snapshot(snapshot or {}),
            round_number=1,
            parent_session_id=None,
            original_mode=False,
            beta_unlocked=beta_unlocked_from_request(vertical),
        ))
        return _remember_free_generation(response, vertical, session_id)

    @app.get("/results/session/<session_id>")
    def session_results(session_id: str):
        return _render_results_snapshot(session_id)

    @app.get("/api/internal/mission-control/openai-usage")
    def mission_control_openai_usage():
        if not _mission_control_authorized(request.headers.get("Authorization", "")):
            return jsonify({"error": "unauthorized"}), 401
        try:
            report = build_openai_usage_report(
                start=_parse_iso_datetime_arg(request.args.get("start")),
                end=_parse_iso_datetime_arg(request.args.get("end")),
                request_type=_optional_query_arg(request.args.get("request_type")),
                model=_optional_query_arg(request.args.get("model")),
                vertical=_optional_query_arg(request.args.get("vertical")),
                success=_parse_bool_arg(request.args.get("success")),
                reporting_window=_optional_query_arg(request.args.get("reporting_window")),
                session_sort=_optional_query_arg(request.args.get("session_sort")) or "timestamp",
                session_sort_direction=(
                    _optional_query_arg(request.args.get("session_sort_direction")) or "desc"
                ),
            )
        except ValueError:
            return jsonify({"error": "invalid_query"}), 400
        return jsonify(report)

    @app.post("/api/react")
    def react():
        payload = request.get_json(silent=True) or request.form
        if not _valid_csrf_token(payload.get("csrf_token")):
            return jsonify({"error": "csrf_token_invalid"}), 403
        session_id = str(payload.get("session_id", ""))
        result_id = str(payload.get("result_id", ""))
        value = str(payload.get("value", ""))

        snapshot = get_session_snapshot(session_id) if session_id else None
        if snapshot is not None:
            vertical = get_vertical(snapshot["session"]["vertical"])
            if not beta_unlocked_from_request(vertical):
                return _access_required_response(vertical, session_id, wants_json=True)

        try:
            reaction = build_public_reaction(
                session_id=session_id,
                result_id=result_id,
                value=value,
            )
        except ReactionError as exc:
            return jsonify({"error": str(exc)}), 400

        try:
            save_reaction(reaction)
        except StorageError as exc:
            return jsonify({"error": str(exc)}), 404

        taste_profile = build_taste_profile(reaction.session_id)
        return jsonify(
            {
                "reaction": to_plain_data(reaction),
                "reaction_counts": get_reaction_counts(reaction.session_id),
                "taste_profile": to_plain_data(taste_profile),
            }
        ), 201

    @app.post("/choose")
    def choose():
        if not _valid_csrf_token(request.form.get("csrf_token")):
            abort(403)
        session_id = str(request.form.get("session_id", ""))
        result_id = str(request.form.get("result_id", ""))
        if not session_id or not result_id:
            abort(400)

        snapshot = get_session_snapshot(session_id)
        if snapshot is None:
            abort(404)
        vertical = get_vertical(snapshot["session"]["vertical"])
        if not beta_unlocked_from_request(vertical):
            return _access_required_response(vertical, session_id)

        try:
            chosen = save_chosen_name(session_id, result_id)
        except StorageError:
            abort(404)

        _queue_keepsake_generation(chosen.id)
        return redirect(url_for("chosen_name", chosen_id=chosen.id))

    @app.post("/refine")
    def refine():
        if not _valid_csrf_token(request.form.get("csrf_token")):
            abort(403)
        session_id = str(request.form.get("session_id", ""))
        instruction = str(request.form.get("instruction", ""))[:REFINEMENT_INSTRUCTION_MAX_LENGTH]
        if not session_id:
            abort(400)

        snapshot = get_session_snapshot(session_id)
        if snapshot is None:
            abort(404)

        reaction_counts = get_reaction_counts(session_id)
        vertical = get_vertical(snapshot["session"]["vertical"])
        if not beta_unlocked_from_request(vertical):
            return _render_results_snapshot(
                session_id,
                status=402,
                refinement_error=beta_unlock_error(vertical),
            )

        if _reaction_total(reaction_counts) < MIN_REACTIONS_FOR_REFINEMENT:
            remaining = MIN_REACTIONS_FOR_REFINEMENT - _reaction_total(reaction_counts)
            noun = "name" if remaining == 1 else "names"
            return _render_results_snapshot(
                session_id,
                status=400,
                refinement_error=f"React to {remaining} more {noun} before generating the next list.",
            )

        try:
            child_session_id, brief, names = refine_session(
                session_id,
                vertical,
                instruction=instruction,
                generator=_generate_names_for_route,
            )
        except StorageError:
            abort(404)

        child_snapshot = get_session_snapshot(child_session_id)
        round_number = int(child_snapshot["session"]["round_number"])
        taste_profile = _taste_profile_from_snapshot(child_snapshot)
        if request.headers.get("X-NamEngine-Progress") == "1":
            return redirect(url_for("session_results", session_id=child_session_id))

        return render_template(
            "results.html",
            vertical=vertical,
            brief=brief,
            names=names,
            trust_cue=build_trust_cue(names),
            session_id=child_session_id,
            reaction_counts=get_reaction_counts(child_session_id),
            reaction_values=_reaction_values(child_snapshot),
            taste_profile=taste_profile,
            round_number=round_number,
            parent_session_id=session_id,
            original_mode=False,
            beta_unlocked=beta_unlocked_from_request(vertical),
        )

    @app.get("/compare/<session_id>")
    def compare(session_id: str):
        snapshot = get_session_snapshot(session_id)
        if snapshot is None:
            abort(404)

        vertical = get_vertical(snapshot["session"]["vertical"])
        if not beta_unlocked_from_request(vertical):
            return _access_required_response(vertical, session_id)

        items = build_compare_items(session_id)
        taste_profile = _taste_profile_from_snapshot(snapshot)
        return render_template(
            "compare.html",
            vertical=vertical,
            session=snapshot["session"],
            items=items,
            taste_profile=taste_profile,
        )

    @app.get("/share/<session_id>")
    def shared_shortlist(session_id: str):
        snapshot = get_session_snapshot(session_id)
        if snapshot is None:
            vertical_slug = next((slug for slug in VERTICALS if session_id.startswith(slug)), None)
            return render_template(
                "share_missing.html",
                session_id=session_id,
                vertical=get_vertical(vertical_slug) if vertical_slug else None,
            ), 410

        vertical = get_vertical(snapshot["session"]["vertical"])
        if not beta_unlocked_from_request(vertical):
            return _access_required_response(vertical, session_id)

        names = [json_loads(row["result_json"]) for row in snapshot["results"]]
        brief = json_loads(snapshot["session"]["brief_json"])
        taste_profile = _taste_profile_from_snapshot(snapshot)
        return render_template(
            "shared_shortlist.html",
            vertical=vertical,
            session=snapshot["session"],
            brief=brief,
            names=names,
            reaction_counts=snapshot["reaction_counts"],
            taste_profile=taste_profile,
        )

    @app.get("/dev/engine-audit")
    def engine_audit_index():
        if not _engine_audit_enabled():
            abort(404)
        vertical_slug = str(request.args.get("vertical") or "baby").strip().lower()
        if vertical_slug not in VERTICALS:
            abort(400)
        limit = min(_positive_int(request.args.get("limit")) or 50, 200)
        return render_template(
            "engine_audit_index.html",
            vertical=get_vertical(vertical_slug),
            selected_vertical=vertical_slug,
            limit=limit,
            sessions=get_recent_audit_sessions(vertical_slug, limit),
            failures=get_failed_generation_audits(vertical_slug, limit),
        )

    @app.get("/dev/engine-audit/<session_id>")
    def engine_audit(session_id: str):
        if not _engine_audit_enabled():
            abort(404)
        snapshot = get_session_snapshot(session_id)
        if snapshot is None:
            abort(404)

        vertical = get_vertical(snapshot["session"]["vertical"])
        return render_template(
            "engine_audit.html",
            vertical=vertical,
            session=snapshot["session"],
            brief=json_loads(snapshot["session"]["brief_json"]),
            names=_names_from_snapshot(snapshot),
            reaction_counts=get_reaction_counts(session_id),
            chosen_names=snapshot["chosen_names"],
            audit=_engine_audit_from_snapshot(snapshot),
        )

    @app.get("/dev/taste-evolution/<session_id>")
    def taste_evolution(session_id: str):
        if not _engine_audit_enabled():
            abort(404)
        snapshot = get_session_snapshot(session_id)
        if snapshot is None:
            abort(404)
        parent_session_id = snapshot["session"].get("parent_session_id")
        if not parent_session_id:
            abort(404)
        parent_snapshot = get_session_snapshot(parent_session_id)
        if parent_snapshot is None:
            abort(404)

        return render_template(
            "taste_evolution.html",
            vertical=get_vertical(snapshot["session"]["vertical"]),
            session=snapshot["session"],
            parent_session=parent_snapshot["session"],
            evolution=build_taste_evolution(parent_snapshot, snapshot),
        )

    @app.get("/dev/eval-report")
    def eval_report():
        if not _engine_audit_enabled():
            abort(404)
        if not _mission_control_authorized(request.headers.get("Authorization", "")):
            abort(404)
        fixtures = load_taste_engine_fixtures()
        limit = _positive_int(request.args.get("limit"))
        use_ai = request.args.get("ai") == "1"
        if limit:
            fixtures = fixtures[:limit]

        results = run_taste_engine_fixture_set(fixtures, use_ai=use_ai)
        summary = summarize_taste_engine_eval(results)
        contrasts = compare_contrast_groups(results)
        return render_template(
            "eval_report.html",
            fixtures=fixtures,
            results=results,
            summary=summary,
            contrasts=contrasts,
            use_ai=use_ai,
            limit=limit,
        )

    @app.get("/<vertical_slug>/name/<session_id>/<result_id>")
    def name_detail(vertical_slug: str, session_id: str, result_id: str):
        if vertical_slug not in VERTICALS:
            abort(404)

        detail = result_detail_from_session(session_id, result_id)
        if detail is None:
            abort(404)

        vertical = get_vertical(detail["session"]["vertical"])
        if vertical.slug != vertical_slug:
            abort(404)
        if not beta_unlocked_from_request(vertical):
            return _access_required_response(vertical, session_id)

        decision_support = build_baby_decision_support(
            detail["result"],
            detail["session"],
            detail["taste_profile"],
            detail["available_results"],
            detail["reaction_value"],
        )

        return render_template(
            "name_detail.html",
            vertical=vertical,
            session=detail["session"],
            result=detail["result"],
            name_fact_card=build_name_fact_card(vertical.slug, detail["result"]),
            reaction_counts=detail["reaction_counts"],
            taste_profile=detail["taste_profile"],
            decision_support=decision_support,
        )

    @app.get("/chosen/<chosen_id>")
    def chosen_name(chosen_id: str):
        snapshot = get_chosen_snapshot(chosen_id)
        if snapshot is None or snapshot["result"] is None:
            abort(404)

        vertical = get_vertical(snapshot["chosen"]["vertical"])
        session_id = str((snapshot.get("session") or {}).get("id") or snapshot["chosen"].get("session_id") or "")
        if not beta_unlocked_from_request(vertical):
            return _access_required_response(vertical, session_id)

        result = to_plain_data(json_loads(snapshot["result"]["result_json"]))
        _queue_keepsake_generation(chosen_id)
        portrait = _keepsake_preview(chosen_id)
        return render_template(
            "chosen.html",
            vertical=vertical,
            chosen=snapshot["chosen"],
            result=result,
            name_fact_card=build_name_fact_card(str(snapshot["chosen"]["vertical"]), result),
            session=snapshot["session"],
            portrait=portrait,
        )

    @app.get("/generated/pet-portraits/<filename>")
    def generated_pet_portrait(filename: str):
        return send_from_directory(generated_image_directory("pet"), filename)

    @app.get("/generated/baby-keepsakes/<filename>")
    def generated_baby_keepsake(filename: str):
        return send_from_directory(generated_image_directory("baby"), filename)

    @app.get("/generated/business-images/<filename>")
    def generated_business_image(filename: str):
        return send_from_directory(generated_image_directory("business"), filename)

    @app.get("/api/chosen/<chosen_id>/portrait")
    def chosen_portrait_status(chosen_id: str):
        snapshot = get_chosen_snapshot(chosen_id)
        if snapshot is None:
            abort(404)

        vertical_slug = str(snapshot["chosen"].get("vertical", ""))
        portrait = _keepsake_preview(chosen_id)
        if portrait and portrait.get("status") not in {"ready", "not_configured", "failed"}:
            _queue_keepsake_generation(chosen_id)
        return jsonify(
            {
                "chosen_id": chosen_id,
                "runtime": keepsake_runtime_config(vertical_slug),
                "portrait": portrait or {"status": "not_attempted"},
            }
        )

    @app.post("/api/chosen/<chosen_id>/portrait/retry")
    def retry_chosen_portrait(chosen_id: str):
        snapshot = get_chosen_snapshot(chosen_id)
        if snapshot is None:
            abort(404)
        vertical = get_vertical(snapshot["chosen"]["vertical"])
        if not beta_unlocked_from_request(vertical):
            session_id = str((snapshot.get("session") or {}).get("id") or snapshot["chosen"].get("session_id") or "")
            return _access_required_response(vertical, session_id, wants_json=True)
        portrait = _queue_keepsake_generation(chosen_id, force_retry=True)
        return jsonify(
            {
                "chosen_id": chosen_id,
                "portrait": portrait or {"status": "not_attempted"},
            }
        )

    @app.route("/feedback", methods=["GET", "POST"])
    def feedback():
        submitted = request.method == "POST"
        if submitted:
            save_feedback_submission(request.form)
        return render_template(
            "feedback.html",
            vertical=get_vertical("pet"),
            submitted=submitted,
            form_data=request.form if submitted else {},
        )

    return app


def json_loads(value: str):
    import json

    return json.loads(value)


def _taste_profile_from_snapshot(snapshot: dict):
    row = snapshot.get("taste_profile")
    if not row:
        return None
    return json_loads(row["profile_json"])


def _names_from_snapshot(snapshot: dict) -> list[NameResult]:
    names: list[NameResult] = []
    for row in snapshot["results"]:
        data = json_loads(row["result_json"])
        data["validation"] = [
            item if isinstance(item, ValidationResult) else ValidationResult(**item)
            for item in data.get("validation", [])
        ]
        names.append(NameResult(**data))
    return names


def _engine_audit_from_snapshot(snapshot: dict) -> dict:
    names = _names_from_snapshot(snapshot)
    first = names[0] if names else None
    metadata = first.metadata if first else {}
    ai_calls = metadata.get("ai_calls") if isinstance(metadata.get("ai_calls"), list) else []
    usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    metrics_totals = {
        "prompt_json_chars": 0,
        "prompt_json_bytes": 0,
        "request_input_chars": 0,
        "output_json_chars": 0,
        "output_json_bytes": 0,
        "raw_response_json_chars": 0,
        "raw_response_json_bytes": 0,
    }
    total_latency_ms = 0
    ai_call_count = 0
    cost_estimate = estimate_ai_calls_cost_usd(
        ai_calls,
        fallback_model=str(metadata.get("model") or ""),
    )
    for call in ai_calls:
        if not isinstance(call, dict):
            continue
        ai_call_count += 1
        try:
            total_latency_ms += int(call.get("latency_ms") or 0)
        except (TypeError, ValueError):
            pass
        usage = call.get("usage") if isinstance(call.get("usage"), dict) else {}
        for key in usage_totals:
            try:
                usage_totals[key] += int(usage.get(key) or 0)
            except (TypeError, ValueError):
                pass
        metrics = call.get("metrics") if isinstance(call.get("metrics"), dict) else {}
        for key in metrics_totals:
            try:
                metrics_totals[key] += int(metrics.get(key) or 0)
            except (TypeError, ValueError):
                pass

    providers = sorted(
        {
            str(name.metadata.get("provider") or name.metadata.get("source") or "unknown")
            for name in names
        }
    )
    return _safe_audit_value(
        {
            "generation_id": metadata.get("generation_id") or snapshot["session"]["id"],
            "prompt_version": metadata.get("prompt_version", "unknown"),
            "intake_schema_version": metadata.get("intake_schema_version", "unknown"),
            "normalizer_version": metadata.get("normalizer_version", "unknown"),
            "intake_adapter_version": metadata.get("intake_adapter_version", "unknown"),
            "canonical_intent_version": metadata.get("canonical_intent_version", "unknown"),
            "engine_pipeline": metadata.get("engine_pipeline", "unknown"),
            "model": metadata.get("model", "unknown"),
            "providers": providers,
            "ai_calls": ai_calls,
            "usage_totals": usage_totals,
            "cost_estimate": cost_estimate,
            "metrics_totals": metrics_totals,
            "ai_call_count": ai_call_count,
            "total_latency_ms": total_latency_ms,
            "taste_strategy": metadata.get("taste_strategy", {}),
            "candidate_pool": metadata.get("candidate_pool", []),
            "rejected_candidates": metadata.get("rejected_candidates", []),
            "result_metadata": metadata,
        }
    )


def _safe_audit_value(value):
    """Redact credential-shaped values before rendering internal audit data."""
    if isinstance(value, dict):
        return {
            key: "[redacted]" if _is_sensitive_audit_key(key) else _safe_audit_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe_audit_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_safe_audit_value(item) for item in value)
    return value


def _is_sensitive_audit_key(key) -> bool:
    normalized = str(key).strip().lower().replace("-", "_")
    return (
        normalized
        in {
            "authorization",
            "cookie",
            "credentials",
            "password",
            "private_key",
            "secret",
            "set_cookie",
            "token",
        }
        or "api_key" in normalized
        or "apikey" in normalized
        or normalized.endswith("_password")
        or normalized.endswith("_private_key")
        or normalized.endswith("_secret")
        or normalized.endswith("_token")
    )


def _positive_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _engine_audit_enabled() -> bool:
    return os.getenv("NAMENGINE_ENABLE_ENGINE_AUDIT") == "1"


def _mission_control_authorized(authorization_header: str) -> bool:
    expected = os.getenv("NAMENGINE_TELEMETRY_TOKEN", "").strip()
    if not expected:
        return False
    prefix = "Bearer "
    if not authorization_header.startswith(prefix):
        return False
    supplied = authorization_header[len(prefix):].strip()
    return bool(supplied) and compare_digest(supplied, expected)


def _parse_iso_datetime_arg(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    # URL query parsing turns an unescaped timezone "+" into a space.
    raw = raw.replace(" ", "+")
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _optional_query_arg(value: str | None) -> str | None:
    raw = str(value or "").strip()
    return raw or None


def _parse_bool_arg(value: str | None) -> bool | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    if raw in {"1", "true", "yes"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    raise ValueError("invalid boolean query parameter")


def _generate_names_for_route(
    vertical,
    brief: NamingBrief,
    *,
    round_number: int = 1,
    taste_summary: str = "",
    taste_profile=None,
    previous_names: list[str] | None = None,
) -> list[NameResult]:
    if _should_use_ai_for_vertical(vertical):
        started_at = time.perf_counter()
        try:
            names = generate_with_router(
                vertical=vertical,
                brief=brief,
                round_number=round_number,
                taste_profile=taste_profile,
                previous_names=previous_names or [],
                providers=[ModelProvider.OPENAI],
                fallback_on_provider_error=vertical.slug != "business",
            )
            if not names:
                raise AIGenerationError("generation returned no usable names")
        except Exception as exc:  # pragma: no cover - live provider behavior
            logger.exception("LLM generation failed for %s", vertical.slug)
            safe_message = "We’re having trouble generating this list right now. Please try again shortly."
            try:
                save_failed_generation_audit(
                    vertical=vertical.slug,
                    provider=ModelProvider.OPENAI.value,
                    model=os.getenv("NAMENGINE_OPENAI_MODEL", DEFAULT_MODEL),
                    prompt_version=prompt_version_for(vertical.slug),
                    latency_ms=int((time.perf_counter() - started_at) * 1000),
                    customer_intake=_audit_customer_intake(brief),
                    exception_type=_generation_exception_type(exc),
                    safe_error_message=safe_message,
                )
            except Exception:  # pragma: no cover - audit failure must not replace product response
                logger.exception("Could not persist failed generation audit for %s", vertical.slug)
            raise NameGenerationUnavailable(
                safe_message
            ) from exc
        for name in names:
            provider = str(name.metadata.get("provider") or name.metadata.get("source") or "").lower()
            is_llm_result = provider in {ModelProvider.OPENAI.value, "ai"}
            if is_llm_result:
                name.metadata.setdefault("source", ModelProvider.OPENAI.value)
                name.metadata.setdefault("provider", ModelProvider.OPENAI.value)
                name.metadata["llm_required"] = True
            else:
                name.metadata.setdefault("source", provider or ModelProvider.FALLBACK.value)
                name.metadata.setdefault("provider", provider or ModelProvider.FALLBACK.value)
                name.metadata["llm_required"] = False
                name.metadata["ai_primary_fallback"] = True
            name.metadata["ai_primary_requested"] = True
        _record_provider_failures_from_fallback(vertical, brief, names)
        if vertical.slug == "business":
            names = enrich_business_domain_info(names)
        return names

    return generate_names(
        vertical,
        brief,
        round_number=round_number,
        taste_summary=taste_summary,
        taste_profile=taste_profile,
        previous_names=previous_names or [],
        use_ai=False,
    )


def _record_provider_failures_from_fallback(vertical, brief: NamingBrief, names: list[NameResult]) -> None:
    if vertical.slug not in {"baby", "pet"}:
        return

    recorded: set[tuple[str, str]] = set()
    for name in names:
        if str(name.metadata.get("provider") or "").lower() != ModelProvider.FALLBACK.value:
            continue
        failures = name.metadata.get("provider_failures")
        if not isinstance(failures, list):
            continue
        for failure in failures:
            if not isinstance(failure, dict):
                continue
            provider = str(failure.get("provider") or ModelProvider.OPENAI.value)
            exception_type = str(failure.get("exception_type") or "generation_error")
            key = (provider, exception_type)
            if key in recorded:
                continue
            recorded.add(key)
            try:
                save_failed_generation_audit(
                    vertical=vertical.slug,
                    provider=provider,
                    model=os.getenv("NAMENGINE_OPENAI_MODEL", DEFAULT_MODEL),
                    prompt_version=prompt_version_for(vertical.slug),
                    latency_ms=int(failure.get("latency_ms") or 0),
                    customer_intake=_audit_customer_intake(brief),
                    exception_type=exception_type,
                    safe_error_message="Provider failed; deterministic fallback returned customer results.",
                )
            except Exception:  # pragma: no cover - audit failure must not replace product response
                logger.exception("Could not persist fallback provider-failure audit for %s", vertical.slug)
        name.metadata.pop("provider_failures", None)


def _generation_exception_type(exc: Exception) -> str:
    stage = getattr(exc, "stage", "")
    if stage:
        return f"{type(exc).__name__}:{stage}"
    return type(exc).__name__


def _audit_customer_intake(brief: NamingBrief) -> dict:
    """Keep the existing audit payload without duplicating canonical context."""
    payload = to_plain_data(brief)
    payload.pop("canonical_intent", None)
    return payload


def _ai_primary_verticals() -> set[str]:
    raw_value = os.getenv("NAMENGINE_AI_PRIMARY_VERTICALS", "baby,pet,business")
    if raw_value.strip().lower() in {"", "none", "off", "false", "0"}:
        return set()
    if raw_value.strip().lower() in {"all", "*"}:
        return set(VERTICALS)
    return {
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    }


def _should_use_ai_for_vertical(vertical) -> bool:
    return vertical.slug in _ai_primary_verticals() and is_ai_generation_configured()


def _result_is_ai_sourced(name: NameResult) -> bool:
    source = str(name.metadata.get("source", "")).lower()
    provider = str(name.metadata.get("provider", "")).lower()
    return source in {"openai", "ai"} or provider in {"openai", "ai"}


def _cached_names_match_current_rules(
    vertical,
    brief: NamingBrief,
    names: list[NameResult],
) -> bool:
    if _should_use_ai_for_vertical(vertical):
        all_ai = all(_result_is_ai_sourced(name) for name in names)
        if vertical.slug == "business":
            # Business is premium-positioning work. Never silently reuse deterministic
            # fallback Business names as if they were successful AI output.
            if not all_ai:
                return False
        else:
            all_current_failure_fallback = all(
                not _result_is_ai_sourced(name)
                and name.metadata.get("ai_primary_requested") is True
                and name.metadata.get("ai_primary_fallback") is True
                for name in names
            )
            if not (all_ai or all_current_failure_fallback):
                return False
    if vertical.slug == "baby":
        if len(filter_results_for_brief(vertical, brief, names)) != len(names):
            return False
        return all(
            "baby_gender_direction" in {item.module for item in name.validation}
            for name in names
        )
    if vertical.slug == "business":
        return all(
            "business_domain" in {item.module for item in name.validation}
            and isinstance(name.metadata.get("domain_info"), dict)
            for name in names
        )
    return True


def _try_generate_keepsake(chosen_id: str):
    snapshot = get_chosen_snapshot(chosen_id)
    if snapshot is None or snapshot["result"] is None:
        return None
    if snapshot["chosen"].get("vertical") not in {"pet", "baby", "business"}:
        return None

    result = to_plain_data(json_loads(snapshot["result"]["result_json"]))
    try:
        return ensure_keepsake_for_chosen(
            snapshot["chosen"],
            result,
            snapshot["session"],
        )
    except Exception as exc:
        logger.warning(
            "Keepsake generation failed for %s: %s: %s",
            chosen_id,
            exc.__class__.__name__,
            safe_provider_error_for_log(exc),
        )
        return None


def _keepsake_preview(chosen_id: str):
    snapshot = get_chosen_snapshot(chosen_id)
    if snapshot is None or snapshot["result"] is None:
        return None
    if snapshot["chosen"].get("vertical") not in {"pet", "baby"}:
        return None

    return keepsake_preview_for_chosen(snapshot["chosen"], snapshot["session"])


def _queue_keepsake_generation(chosen_id: str, *, force_retry: bool = False):
    snapshot = get_chosen_snapshot(chosen_id)
    if snapshot is None or snapshot["result"] is None:
        return None
    if snapshot["chosen"].get("vertical") not in {"pet", "baby"}:
        return None

    result = to_plain_data(json_loads(snapshot["result"]["result_json"]))
    portrait = prepare_keepsake_for_chosen(
        snapshot["chosen"],
        result,
        snapshot["session"],
        force_retry=force_retry,
    )
    if not portrait or portrait.get("status") in {"ready", "not_configured", "failed"}:
        return portrait

    with _portrait_jobs_lock:
        if chosen_id in _portrait_jobs:
            return portrait
        _portrait_jobs.add(chosen_id)

    def run() -> None:
        try:
            _try_generate_keepsake(chosen_id)
        finally:
            with _portrait_jobs_lock:
                _portrait_jobs.discard(chosen_id)

    Thread(target=run, daemon=True).start()
    return portrait


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
