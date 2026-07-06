"""Business domain availability quick checks.

The GoDaddy check is a launch signal, not a guarantee. Names still need final
domain, trademark, and social-handle review before purchase or public use.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from namengine.core.schemas import NameResult


logger = logging.getLogger(__name__)
DEFAULT_DOMAIN_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "domain_cache.json"


def domain_slug(name: str) -> str:
    """Create the practical domain stem used for quick availability checks."""
    cleaned = re.sub(r"\band\b", "", (name or "").lower())
    cleaned = re.sub(
        r"\b(co|company|inc|llc|studio|studios|group|works)\b",
        "",
        cleaned,
    )
    cleaned = re.sub(r"[^a-z0-9]+", "", cleaned)
    return cleaned or "name"


def domain_status(domain: str, status: str = "unknown", label: str = "") -> dict[str, str]:
    if not label:
        label = {
            "available": "Available",
            "taken": "Taken",
            "premium": "Premium",
            "not_checked": "Not checked",
            "unknown": "Not verified",
        }.get(status, status.replace("_", " ").title())
    return {
        "domain": domain,
        "status": status,
        "label": label,
        "class": status.replace("_", "-"),
    }


def domain_status_from_godaddy(domain: str, payload: dict[str, Any] | None) -> dict[str, str]:
    available = payload.get("available") if isinstance(payload, dict) else None
    premium_threshold = int(os.getenv("GODADDY_PREMIUM_PRICE_THRESHOLD", "100000000"))
    price = payload.get("price") if isinstance(payload, dict) else None
    is_premium = bool(payload.get("premium")) if isinstance(payload, dict) else False
    if isinstance(price, int) and price >= premium_threshold:
        is_premium = True

    if available is True:
        if is_premium:
            return domain_status(domain, "premium", "Premium")
        return domain_status(domain, "available", "Available")
    if available is False:
        return domain_status(domain, "taken", "Taken")
    return domain_status(domain)


def build_domain_info(name: str) -> dict[str, Any]:
    base = domain_slug(name)
    primary = f"{base}.com"
    alternates = [f"get{base}.com", f"{base}.co", f"{base}.io"]
    if len(base) > 10:
        alternates = [f"hello{base}.com", f"{base}.co", f"{base}.io"]
    return {
        "base": base,
        "primary": primary,
        "alternates": alternates,
        "display_domain": primary,
        "display_status": domain_status(primary, "unknown"),
        "note": "",
    }


def enrich_business_domain_info(results: list[NameResult]) -> list[NameResult]:
    """Attach a domain quick-check payload to each Business name result."""
    if not results:
        return results

    domain_infos: list[dict[str, Any]] = []
    domains_to_check: list[str] = []
    for result in results:
        info = build_domain_info(result.name)
        domain_infos.append(info)
        domains_to_check.append(info["primary"])
        domains_to_check.extend(info["alternates"])

    statuses = check_domain_availability(domains_to_check)
    for result, info in zip(results, domain_infos):
        options = [info["primary"], *info["alternates"]]
        status_options = [statuses.get(domain, domain_status(domain)) for domain in options]
        display_status = choose_display_domain(status_options)
        info["display_domain"] = display_status["domain"]
        info["display_status"] = display_status
        result.metadata["domain_info"] = info

    return results


def choose_display_domain(statuses: list[dict[str, str]]) -> dict[str, str]:
    for status in statuses:
        if status.get("status") == "available":
            return status
    for status in statuses:
        if status.get("status") not in {"unknown", "not_checked"}:
            return status
    return statuses[0] if statuses else domain_status("name.com")


def check_domain_availability(domains: list[str]) -> dict[str, dict[str, str]]:
    unique_domains = list(dict.fromkeys(domain for domain in domains if domain))
    if not unique_domains:
        return {}

    credentials = godaddy_credentials()
    if credentials is None:
        return {
            domain: domain_status(domain, "not_checked", "Not checked")
            for domain in unique_domains
        }

    cache = load_domain_cache()
    results: dict[str, dict[str, str]] = {}
    pending: list[str] = []
    for domain in unique_domains:
        cached = cached_domain_status(domain, cache)
        if cached is not None:
            results[domain] = cached
        else:
            pending.append(domain)

    if pending:
        max_workers = min(6, len(pending))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(godaddy_domain_available, domain, credentials): domain
                for domain in pending
            }
            for future in as_completed(future_map):
                domain = future_map[future]
                try:
                    status = future.result()
                except Exception as exc:  # pragma: no cover - defensive network fallback
                    logger.warning("GoDaddy domain quick check failed for %s: %s", domain, exc)
                    status = domain_status(domain)
                results[domain] = status
                cache[domain] = {
                    "checked_at": time.time(),
                    "status": status,
                }
        save_domain_cache(cache)

    return results


def godaddy_credentials() -> tuple[str, str] | None:
    api_key = os.getenv("GODADDY_API_KEY", "").strip()
    api_secret = os.getenv("GODADDY_API_SECRET", "").strip()
    if not api_key or not api_secret:
        return None
    return api_key, api_secret


def godaddy_domain_available(domain: str, credentials: tuple[str, str]) -> dict[str, str]:
    api_key, api_secret = credentials
    base_url = os.getenv("GODADDY_API_BASE", "https://api.godaddy.com").rstrip("/")
    timeout = float(os.getenv("GODADDY_TIMEOUT_SECONDS", "4"))
    url = f"{base_url}/v1/domains/available?domain={quote(domain)}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"sso-key {api_key}:{api_secret}",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("GoDaddy domain quick check failed for %s: %s", domain, exc)
        return domain_status(domain)
    return domain_status_from_godaddy(domain, payload)


def load_domain_cache() -> dict[str, dict[str, Any]]:
    path = domain_cache_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_domain_cache(cache: dict[str, dict[str, Any]]) -> None:
    path = domain_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def cached_domain_status(
    domain: str,
    cache: dict[str, dict[str, Any]],
) -> dict[str, str] | None:
    entry = cache.get(domain)
    if not isinstance(entry, dict):
        return None

    checked_at = float(entry.get("checked_at") or 0)
    status = entry.get("status")
    if not isinstance(status, dict):
        return None

    ttl = int(os.getenv("DOMAIN_CACHE_TTL_SECONDS", str(6 * 60 * 60)))
    if status.get("status") in {"unknown", "not_checked"}:
        ttl = int(os.getenv("DOMAIN_UNKNOWN_CACHE_TTL_SECONDS", str(15 * 60)))
    if time.time() - checked_at > ttl:
        return None
    return status


def domain_cache_path() -> Path:
    configured_path = os.getenv("DOMAIN_CACHE_PATH", "").strip()
    if configured_path:
        return Path(configured_path)

    try:
        from namengine.core.storage import get_database_path

        return get_database_path().parent / "domain_cache.json"
    except Exception:  # pragma: no cover - fallback for unusual import/runtime states
        return DEFAULT_DOMAIN_CACHE_PATH
