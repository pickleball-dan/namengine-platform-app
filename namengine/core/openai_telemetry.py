"""Structured OpenAI usage telemetry for production log search."""

from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import math
import os
from datetime import UTC, date, datetime, time as datetime_time, timedelta
from pathlib import Path
from typing import Any, Iterator


TEXT_USAGE_PREFIX = "NAMENGINE_OPENAI_USAGE"
IMAGE_USAGE_PREFIX = "NAMENGINE_OPENAI_IMAGE_USAGE"
DEFAULT_REPORT_DAYS = 30
MAX_REPORT_DAYS = 90
DEFAULT_MAX_SCAN_RECORDS = 250_000

logger = logging.getLogger(__name__)
_current_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "namengine_openai_telemetry_context",
    default={},
)


class TelemetryQueryError(ValueError):
    """Raised when a telemetry report query is invalid or unbounded."""


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
                "usage_available": _attr_or_item(response, "usage") is not None,
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
        pass
    try:
        _append_jsonl_event(prefix, payload)
    except Exception:  # pragma: no cover - telemetry must never affect generation
        return


def _append_jsonl_event(prefix: str, payload: dict[str, Any]) -> None:
    """Append only aggregate-safe fields from the existing telemetry event."""
    target = os.getenv("NAMENGINE_OPENAI_TELEMETRY_PATH", "").strip()
    if not target:
        return
    if prefix == IMAGE_USAGE_PREFIX:
        event = {
            "timestamp": payload.get("timestamp"),
            "request_type": "images.generate",
            "model": payload.get("model"),
            "latency_ms": payload.get("duration_ms"),
            "success": payload.get("status") == "success",
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "image_count": payload.get("number_of_images"),
            "context": payload.get("action"),
            "error_type": payload.get("error_type"),
        }
    elif prefix == TEXT_USAGE_PREFIX:
        usage_available = payload.get("usage_available") is True
        event = {
            "timestamp": payload.get("timestamp"),
            "request_type": "responses.create",
            "model": payload.get("model_returned") or payload.get("model_requested"),
            "latency_ms": payload.get("duration_ms"),
            "success": payload.get("status") == "success",
            "input_tokens": payload.get("input_tokens") if usage_available else None,
            "output_tokens": payload.get("output_tokens") if usage_available else None,
            "total_tokens": payload.get("total_tokens") if usage_available else None,
            "context": payload.get("action"),
            "error_type": payload.get("error_type"),
        }
    else:
        return
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")


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


def aggregate_openai_telemetry(
    *,
    start: str | None = None,
    end: str | None = None,
    request_type: str | None = None,
    model: str | None = None,
    success: str | bool | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return bounded aggregates from the configured telemetry JSONL file."""
    range_start, range_end = _report_range(start, end, now=now)
    success_filter = _success_filter(success)
    request_type_filter = _bounded_filter(request_type, "request_type")
    model_filter = _bounded_filter(model, "model")
    scan_limit = _max_scan_records()
    records_scanned = 0
    scan_truncated = False

    summary = _metric_bucket()
    by_day: dict[str, dict[str, Any]] = {}
    by_request_type: dict[str, dict[str, Any]] = {}
    by_model: dict[str, dict[str, Any]] = {}
    failures_by_error_type: dict[str, int] = {}
    slowest_categories: dict[str, dict[str, Any]] = {}
    missing_usage: dict[tuple[str, str], int] = {}

    for event in _telemetry_events(scan_limit=scan_limit):
        if event is _SCAN_TRUNCATED:
            scan_truncated = True
            break
        records_scanned += 1
        if not isinstance(event, dict):
            continue
        timestamp = _event_timestamp(event.get("timestamp"))
        if timestamp is None or not (range_start <= timestamp < range_end):
            continue
        event_request_type = _safe_label(event.get("request_type"))
        event_model = _safe_label(event.get("model"), fallback="Unreported")
        event_success = event.get("success")
        if not isinstance(event_success, bool):
            continue
        if request_type_filter is not None and event_request_type != request_type_filter:
            continue
        if model_filter is not None and event_model != model_filter:
            continue
        if success_filter is not None and event_success is not success_filter:
            continue

        normalized = {
            "success": event_success,
            "latency_ms": _nonnegative_number(event.get("latency_ms")),
            "input_tokens": _nonnegative_int(event.get("input_tokens")),
            "output_tokens": _nonnegative_int(event.get("output_tokens")),
            "total_tokens": _nonnegative_int(event.get("total_tokens")),
            "image_count": _nonnegative_int(event.get("image_count")),
            "request_type": event_request_type,
            "model": event_model,
        }
        missing_tokens = normalized["total_tokens"] is None
        _add_metric(summary, normalized, missing_tokens=missing_tokens)
        _add_group_metric(by_day, timestamp.date().isoformat(), normalized, missing_tokens)
        _add_group_metric(by_request_type, event_request_type, normalized, missing_tokens)
        _add_group_metric(by_model, event_model, normalized, missing_tokens)

        category = _safe_label(event.get("context"), fallback=event_request_type)
        _add_group_metric(slowest_categories, category, normalized, missing_tokens)
        if not event_success:
            error_type = _safe_label(event.get("error_type"), fallback="Unreported")
            failures_by_error_type[error_type] = failures_by_error_type.get(error_type, 0) + 1
        if missing_tokens:
            key = (event_request_type, event_model)
            missing_usage[key] = missing_usage.get(key, 0) + 1

    return {
        "range": {
            "start": range_start.isoformat(),
            "end": range_end.isoformat(),
            "end_exclusive": True,
            "maximum_days": MAX_REPORT_DAYS,
        },
        "filters": {
            "request_type": request_type_filter,
            "model": model_filter,
            "success": success_filter,
        },
        "scan": {
            "truncated": scan_truncated,
            "records_scanned": records_scanned,
            "scan_limit": scan_limit,
        },
        "summary": _finalize_metric(summary),
        "requests_by_day": _finalize_groups(by_day, "date"),
        "requests_by_request_type": _finalize_groups(by_request_type, "request_type"),
        "requests_by_model": _finalize_groups(by_model, "model"),
        "failures_by_error_type": [
            {"error_type": key, "failure_count": value}
            for key, value in sorted(failures_by_error_type.items(), key=lambda item: (-item[1], item[0]))
        ],
        "slowest_request_categories": sorted(
            _finalize_groups(slowest_categories, "category"),
            key=lambda item: (-item["average_latency_ms"], item["category"]),
        ),
        "requests_with_unavailable_token_usage": [
            {"request_type": key[0], "model": key[1], "request_count": value}
            for key, value in sorted(missing_usage.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


def _report_range(
    start: str | None,
    end: str | None,
    *,
    now: datetime | None,
) -> tuple[datetime, datetime]:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    current = current.astimezone(UTC)
    range_end = _parse_boundary(end, is_end=True) if end else current
    range_start = _parse_boundary(start, is_end=False) if start else range_end - timedelta(days=DEFAULT_REPORT_DAYS)
    if range_start >= range_end:
        raise TelemetryQueryError("start must be before end")
    if range_end - range_start > timedelta(days=MAX_REPORT_DAYS):
        raise TelemetryQueryError(f"date range cannot exceed {MAX_REPORT_DAYS} days")
    return range_start, range_end


def _parse_boundary(value: str, *, is_end: bool) -> datetime:
    text = str(value).strip()
    try:
        if len(text) == 10:
            parsed_date = date.fromisoformat(text)
            parsed = datetime.combine(parsed_date, datetime_time.min, tzinfo=UTC)
            return parsed + timedelta(days=1) if is_end else parsed
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TelemetryQueryError("dates must use ISO-8601 format") from exc
    if parsed.tzinfo is None:
        raise TelemetryQueryError("date-times must include a timezone")
    return parsed.astimezone(UTC)


def _success_filter(value: str | bool | None) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise TelemetryQueryError("success must be true or false")


def _bounded_filter(value: str | None, name: str) -> str | None:
    if value in (None, ""):
        return None
    normalized = str(value).strip()
    if not normalized or len(normalized) > 200:
        raise TelemetryQueryError(f"{name} is invalid")
    return normalized


_SCAN_TRUNCATED = object()


def _max_scan_records() -> int:
    raw_value = os.getenv("NAMENGINE_OPENAI_TELEMETRY_MAX_SCAN_RECORDS", "").strip()
    if not raw_value:
        return DEFAULT_MAX_SCAN_RECORDS
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_SCAN_RECORDS
    return value if value > 0 else DEFAULT_MAX_SCAN_RECORDS


def _telemetry_events(*, scan_limit: int):
    target = os.getenv("NAMENGINE_OPENAI_TELEMETRY_PATH", "").strip()
    if not target:
        return
    records_scanned = 0
    try:
        with Path(target).open("r", encoding="utf-8") as handle:
            for line in handle:
                if records_scanned >= scan_limit:
                    yield _SCAN_TRUNCATED
                    return
                records_scanned += 1
                try:
                    event = json.loads(line)
                except (json.JSONDecodeError, UnicodeError):
                    yield None
                    continue
                yield event if isinstance(event, dict) else None
    except OSError:
        return


def _event_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _safe_label(value: Any, *, fallback: str = "Unreported") -> str:
    if not isinstance(value, str):
        return fallback
    normalized = " ".join(value.split()).strip()
    return normalized[:200] if normalized else fallback


def _nonnegative_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number >= 0 else None


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        return None
    return int(number)


def _metric_bucket() -> dict[str, Any]:
    return {
        "request_count": 0,
        "success_count": 0,
        "failure_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "latency_total_ms": 0.0,
        "latency_count": 0,
        "maximum_latency_ms": 0.0,
        "image_generation_count": 0,
        "requests_missing_token_usage": 0,
    }


def _add_metric(bucket: dict[str, Any], event: dict[str, Any], *, missing_tokens: bool) -> None:
    bucket["request_count"] += 1
    if event["success"]:
        bucket["success_count"] += 1
    else:
        bucket["failure_count"] += 1
    for token_key in ("input_tokens", "output_tokens", "total_tokens"):
        bucket[token_key] += event[token_key] or 0
    latency = event["latency_ms"]
    if latency is not None:
        bucket["latency_total_ms"] += latency
        bucket["latency_count"] += 1
        bucket["maximum_latency_ms"] = max(bucket["maximum_latency_ms"], latency)
    if event["success"] and event["request_type"] == "images.generate":
        bucket["image_generation_count"] += event["image_count"] or 0
    if missing_tokens:
        bucket["requests_missing_token_usage"] += 1


def _add_group_metric(
    groups: dict[str, dict[str, Any]],
    key: str,
    event: dict[str, Any],
    missing_tokens: bool,
) -> None:
    bucket = groups.setdefault(key, _metric_bucket())
    _add_metric(bucket, event, missing_tokens=missing_tokens)


def _finalize_metric(bucket: dict[str, Any]) -> dict[str, Any]:
    request_count = bucket["request_count"]
    latency_count = bucket.pop("latency_count")
    latency_total = bucket.pop("latency_total_ms")
    bucket["success_rate"] = round(bucket["success_count"] * 100 / request_count, 1) if request_count else 0.0
    bucket["average_latency_ms"] = round(latency_total / latency_count, 1) if latency_count else 0.0
    bucket["maximum_latency_ms"] = round(bucket["maximum_latency_ms"], 1)
    return bucket


def _finalize_groups(groups: dict[str, dict[str, Any]], key_name: str) -> list[dict[str, Any]]:
    return [
        {key_name: key, **_finalize_metric(value)}
        for key, value in sorted(groups.items())
    ]
