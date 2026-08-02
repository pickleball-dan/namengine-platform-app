"""Internal usage telemetry report for Mission Control."""

from __future__ import annotations

import json
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from namengine.core.cost_estimates import estimate_ai_call_cost_usd
from namengine.core.storage import connect, initialize_database


def build_openai_usage_report(
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    request_type: str | None = None,
    model: str | None = None,
    vertical: str | None = None,
    success: bool | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return aggregate AI-call usage in the shape Mission Control expects."""
    initialize_database(db_path)
    events = _successful_call_events(db_path)
    failure_events = _failure_events(db_path)
    all_events = events + failure_events
    filtered = [
        event
        for event in all_events
        if _in_range(event["timestamp"], start, end)
        and (request_type is None or event["request_type"] == request_type)
        and (model is None or event["model"] == model)
        and (vertical is None or event["vertical"] == vertical)
        and (success is None or event["success"] is success)
    ]
    successful = [event for event in filtered if event["success"]]
    failures = [event for event in filtered if not event["success"]]
    return {
        "range": {
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
        },
        "summary": _metric_row(filtered),
        "requests_by_day": _group_rows(successful, "date"),
        "requests_by_request_type": _group_rows(successful, "request_type"),
        "requests_by_model": _group_rows(successful, "model"),
        "requests_by_session": _session_rows(successful),
        "requests_by_vertical": _group_rows(successful, "vertical"),
        "failures_by_error_type": _failure_rows(failures),
        "slowest_request_categories": _slowest_rows(successful),
        "requests_with_unavailable_token_usage": _missing_usage_rows(successful),
    }


def _successful_call_events(db_path: Path | None) -> list[dict[str, Any]]:
    with closing(connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT
                sessions.created_at,
                sessions.vertical,
                sessions.id AS session_id,
                (SELECT COUNT(*) FROM name_results WHERE session_id = sessions.id) AS generated_name_count,
                (SELECT result_json FROM name_results
                    WHERE session_id = sessions.id ORDER BY id LIMIT 1) AS first_result_json
            FROM sessions
            ORDER BY sessions.created_at DESC, sessions.id DESC
            """
        ).fetchall()

    events: list[dict[str, Any]] = []
    for row in rows:
        result = _json_object(row["first_result_json"])
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        calls = metadata.get("ai_calls") if isinstance(metadata.get("ai_calls"), list) else []
        fallback_model = str(metadata.get("model") or "unknown")
        timestamp = _parse_timestamp(row["created_at"])
        for index, call in enumerate(calls):
            if not isinstance(call, dict):
                continue
            usage = call.get("usage") if isinstance(call.get("usage"), dict) else {}
            estimate = estimate_ai_call_cost_usd(call, fallback_model=fallback_model) or {}
            input_tokens = _safe_int(usage.get("input_tokens"))
            output_tokens = _safe_int(usage.get("output_tokens"))
            total_tokens = _safe_int(usage.get("total_tokens")) or input_tokens + output_tokens
            events.append(
                {
                    "timestamp": timestamp,
                    "date": timestamp.date().isoformat(),
                    "success": True,
                    "request_type": str(call.get("stage") or call.get("schema_name") or "generation"),
                    "model": str(call.get("model") or fallback_model or "unknown"),
                    "vertical": str(row["vertical"] or "unknown"),
                    "session_id": str(row["session_id"]),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "latency_ms": _safe_int(call.get("latency_ms")),
                    "estimated_spend_usd": float(estimate.get("estimated_cost_usd") or 0.0),
                    "image_generation_count": 0,
                    "generated_name_count": _safe_int(row["generated_name_count"]) if index == 0 else 0,
                    "missing_token_usage": total_tokens == 0,
                    "error_type": "",
                }
            )
    return events


def _failure_events(db_path: Path | None) -> list[dict[str, Any]]:
    with closing(connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT created_at, vertical, provider, model, prompt_version, latency_ms, exception_type
            FROM failed_generation_audits
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        timestamp = _parse_timestamp(row["created_at"])
        events.append(
            {
                "timestamp": timestamp,
                "date": timestamp.date().isoformat(),
                "success": False,
                "request_type": str(row["prompt_version"] or "generation"),
                "model": str(row["model"] or "unknown"),
                "vertical": str(row["vertical"] or "unknown"),
                "session_id": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_ms": _safe_int(row["latency_ms"]),
                "estimated_spend_usd": 0.0,
                "image_generation_count": 0,
                "generated_name_count": 0,
                "missing_token_usage": True,
                "error_type": str(row["exception_type"] or "generation_error"),
            }
        )
    return events


def _metric_row(events: list[dict[str, Any]]) -> dict[str, Any]:
    request_count = len(events)
    success_count = sum(1 for event in events if event["success"])
    failure_count = request_count - success_count
    latency_values = [event["latency_ms"] for event in events if event["latency_ms"] > 0]
    generated_names = sum(_safe_int(event.get("generated_name_count")) for event in events if event["success"])
    return {
        "request_count": request_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": round(success_count / request_count * 100, 1) if request_count else 0.0,
        "input_tokens": sum(event["input_tokens"] for event in events),
        "output_tokens": sum(event["output_tokens"] for event in events),
        "total_tokens": sum(event["total_tokens"] for event in events),
        "average_latency_ms": round(sum(latency_values) / len(latency_values), 1) if latency_values else 0.0,
        "maximum_latency_ms": max(latency_values) if latency_values else 0,
        "image_generation_count": sum(event["image_generation_count"] for event in events),
        "requests_missing_token_usage": sum(1 for event in events if event["missing_token_usage"]),
        "estimated_spend_usd": round(sum(event["estimated_spend_usd"] for event in events), 6),
        "generated_name_count": generated_names,
    }


def _group_rows(events: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[str(event[key])].append(event)
    rows = [{key: value, **_metric_row(items)} for value, items in grouped.items()]
    return sorted(rows, key=lambda row: str(row[key]), reverse=(key == "date"))


def _failure_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, int] = defaultdict(int)
    for event in events:
        grouped[str(event.get("error_type") or "generation_error")] += 1
    return [
        {"error_type": error_type, "failure_count": count}
        for error_type, count in sorted(grouped.items(), key=lambda item: item[1], reverse=True)
    ]


def _session_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        session_id = str(event.get("session_id") or "unknown")
        grouped[session_id].append(event)

    rows: list[dict[str, Any]] = []
    for session_id, items in grouped.items():
        latest_timestamp = max(event["timestamp"] for event in items)
        verticals = sorted({str(event.get("vertical") or "unknown") for event in items})
        models = sorted({str(event.get("model") or "unknown") for event in items})
        request_types = sorted({str(event.get("request_type") or "generation") for event in items})
        rows.append(
            {
                "session_id": session_id,
                "date": latest_timestamp.date().isoformat(),
                "vertical": verticals[0] if len(verticals) == 1 else "mixed",
                "model": models[0] if len(models) == 1 else "mixed",
                "request_types": request_types,
                **_metric_row(items),
            }
        )
    return sorted(rows, key=lambda row: (row["date"], row["estimated_spend_usd"]), reverse=True)


def _slowest_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = _group_rows(events, "request_type")
    for row in rows:
        row["category"] = row.pop("request_type")
    return sorted(rows, key=lambda row: row["average_latency_ms"], reverse=True)[:8]


def _missing_usage_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], int] = defaultdict(int)
    for event in events:
        if event["missing_token_usage"]:
            grouped[(event["request_type"], event["model"])] += 1
    return [
        {"request_type": request_type, "model": model, "request_count": count}
        for (request_type, model), count in sorted(grouped.items(), key=lambda item: item[1], reverse=True)
    ]


def _in_range(timestamp: datetime, start: datetime | None, end: datetime | None) -> bool:
    return (start is None or timestamp >= start) and (end is None or timestamp <= end)


def _parse_timestamp(value: Any) -> datetime:
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
