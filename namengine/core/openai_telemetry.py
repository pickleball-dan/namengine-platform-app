"""Structured OpenAI usage telemetry for production log search."""

from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, Iterator


TEXT_USAGE_PREFIX = "NAMENGINE_OPENAI_USAGE"
IMAGE_USAGE_PREFIX = "NAMENGINE_OPENAI_IMAGE_USAGE"

logger = logging.getLogger(__name__)
_current_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "namengine_openai_telemetry_context",
    default={},
)


@contextlib.contextmanager
def openai_telemetry_context(**context: Any) -> Iterator[None]:
    """Attach non-sensitive request/session metadata to OpenAI usage logs."""
    parent = dict(_current_context.get() or {})
    parent.update({key: value for key, value in context.items() if value is not None})
    token = _current_context.set(parent)
    try:
        yield
    finally:
        _current_context.reset(token)


def current_openai_telemetry_context() -> dict[str, Any]:
    return dict(_current_context.get() or {})


def log_text_usage(
    *,
    response: Any = None,
    model_requested: str | None = None,
    duration_ms: int | None = None,
    status: str,
    retry_number: int | None = None,
    fallback_used: bool | None = None,
    error_type: str | None = None,
    action: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Emit one structured text-generation usage line; never raise."""
    try:
        usage = extract_text_usage(_attr_or_item(response, "usage"))
        event_context = current_openai_telemetry_context()
        if context:
            event_context.update({key: value for key, value in context.items() if value is not None})
        payload = _base_payload(event_context)
        payload.update(
            {
                "action": _string_or_none(action or event_context.get("action")),
                "model_requested": _string_or_none(model_requested),
                "model_returned": _string_or_none(_attr_or_item(response, "model")) or model_requested,
                "response_id": _string_or_none(_attr_or_item(response, "id")),
                "input_tokens": usage["input_tokens"],
                "cached_input_tokens": usage["cached_input_tokens"],
                "output_tokens": usage["output_tokens"],
                "reasoning_tokens": usage["reasoning_tokens"],
                "total_tokens": usage["total_tokens"],
                "duration_ms": _int_or_zero(duration_ms),
                "status": status,
                "retry_number": _int_or_zero(
                    retry_number if retry_number is not None else event_context.get("retry_number")
                ),
                "fallback_used": bool(fallback_used) if fallback_used is not None else bool(event_context.get("fallback_used", False)),
                "error_type": _string_or_none(error_type),
            }
        )
        _emit(TEXT_USAGE_PREFIX, payload)
    except Exception:  # pragma: no cover - telemetry must never affect generation
        return


def log_image_usage(
    *,
    response: Any = None,
    chosen_id: str | None = None,
    session_id: str | None = None,
    vertical: str | None = None,
    action: str | None = None,
    model: str | None = None,
    size: str | None = None,
    quality: str | None = None,
    number_of_images: int | None = None,
    duration_ms: int | None = None,
    status: str,
    retry_number: int | None = None,
    fallback_used: bool | None = None,
    error_type: str | None = None,
) -> None:
    """Emit one structured image-generation usage line; never raise."""
    try:
        payload = {
            "timestamp": _timestamp(),
            "environment": _environment(),
            "chosen_id": _string_or_none(chosen_id),
            "session_id": _string_or_none(session_id),
            "vertical": _string_or_none(vertical),
            "action": _string_or_none(action),
            "model": _string_or_none(model),
            "response_id": _string_or_none(_attr_or_item(response, "id")),
            "size": _string_or_none(size),
            "quality": _string_or_none(quality),
            "number_of_images": _int_or_zero(number_of_images),
            "duration_ms": _int_or_zero(duration_ms),
            "status": status,
            "retry_number": _int_or_zero(retry_number),
            "fallback_used": bool(fallback_used) if fallback_used is not None else False,
            "error_type": _string_or_none(error_type),
        }
        _emit(IMAGE_USAGE_PREFIX, payload)
    except Exception:  # pragma: no cover - telemetry must never affect generation
        return


def extract_text_usage(usage: Any) -> dict[str, int]:
    """Extract actual token counts returned by OpenAI without estimating."""
    if usage is None:
        return _zero_usage()
    input_details = _attr_or_item(usage, "input_tokens_details") or _attr_or_item(usage, "prompt_tokens_details")
    output_details = _attr_or_item(usage, "output_tokens_details") or _attr_or_item(usage, "completion_tokens_details")
    return {
        "input_tokens": _first_int(usage, "input_tokens", "prompt_tokens"),
        "cached_input_tokens": _first_int(
            input_details,
            "cached_input_tokens",
            "cached_tokens",
            "cache_read_input_tokens",
        ),
        "output_tokens": _first_int(usage, "output_tokens", "completion_tokens"),
        "reasoning_tokens": _first_int(output_details, "reasoning_tokens"),
        "total_tokens": _first_int(usage, "total_tokens"),
    }


def _zero_usage() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
    }


def _base_payload(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": _timestamp(),
        "environment": _environment(),
        "session_id": _string_or_none(context.get("session_id")),
        "parent_session_id": _string_or_none(context.get("parent_session_id")),
        "vertical": _string_or_none(context.get("vertical")),
        "action": _string_or_none(context.get("action")),
        "round_number": _int_or_none(context.get("round_number")),
    }


def _emit(prefix: str, payload: dict[str, Any]) -> None:
    try:
        logger.warning("%s %s", prefix, json.dumps(payload, separators=(",", ":"), sort_keys=True))
    except Exception:  # pragma: no cover - logging backend failure must be swallowed
        return


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _environment() -> str | None:
    return (
        os.getenv("NAMENGINE_ENV")
        or os.getenv("RENDER_SERVICE_NAME")
        or os.getenv("RENDER_ENV")
        or os.getenv("FLASK_ENV")
    )


def _attr_or_item(value: Any, key: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _first_int(source: Any, *keys: str) -> int:
    for key in keys:
        value = _attr_or_item(source, key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
    return 0


def _int_or_zero(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _int_or_none(value: Any) -> int | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:200] or None
