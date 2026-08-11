"""Internal usage telemetry report for Mission Control."""

from __future__ import annotations

import json
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from namengine.core.cost_estimates import estimate_ai_call_cost_usd
from namengine.core.storage import connect, initialize_database


NORMAL_ENGINE_STAGES = (
    "taste_interpreter_v1",
    "candidate_generator_v1",
    "critic_ranker_finalizer_v1",
)
DEFAULT_REPORTING_WINDOW = "last_24_hours"
SESSION_SORT_FIELDS = {
    "timestamp",
    "date",
    "session_id",
    "vertical",
    "model",
    "request_count",
    "success_count",
    "failure_count",
    "success_rate",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "average_latency_ms",
    "maximum_latency_ms",
    "image_generation_count",
    "requests_missing_token_usage",
    "estimated_spend_usd",
    "generated_name_count",
}


def build_openai_usage_report(
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    request_type: str | None = None,
    model: str | None = None,
    vertical: str | None = None,
    success: bool | None = None,
    reporting_window: str | None = DEFAULT_REPORTING_WINDOW,
    session_sort: str = "timestamp",
    session_sort_direction: str = "desc",
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return aggregate AI-call usage in the shape Mission Control expects."""
    start, end, applied_reporting_window = _resolve_report_range(start, end, reporting_window)
    session_sort, session_sort_direction = _resolve_session_sort(session_sort, session_sort_direction)
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
            "reporting_window": applied_reporting_window,
        },
        "session_sort": {
            "sort_by": session_sort,
            "direction": session_sort_direction,
        },
        "summary": _metric_row(filtered),
        "requests_by_day": _group_rows(successful, "date"),
        "requests_by_request_type": _group_rows(successful, "request_type"),
        "usage_exceptions": _usage_exception_rows(successful, failures),
        "requests_by_model": _group_rows(successful, "model"),
        "requests_by_session": _session_rows(
            successful,
            sort_by=session_sort,
            direction=session_sort_direction,
        ),
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


def _usage_exception_rows(
    successful: list[dict[str, Any]], failures: list[dict[str, Any]]
) -> dict[str, Any]:
    normal_stage_set = set(NORMAL_ENGINE_STAGES)
    unexpected = [event for event in successful if event["request_type"] not in normal_stage_set]
    normal = [event for event in successful if event["request_type"] in normal_stage_set]
    return {
        "normal_pipeline": list(NORMAL_ENGINE_STAGES),
        "summary": {
            "normal_request_count": len(normal),
            "exception_request_count": len(unexpected) + len(failures),
            "unexpected_request_type_count": len(unexpected),
            "failure_count": len(failures),
            "pipeline_anomaly_session_count": len(_pipeline_anomaly_rows(successful)),
            "requests_missing_token_usage": sum(
                1 for event in successful if event["missing_token_usage"]
            ),
        },
        "unexpected_request_types": _unexpected_request_type_rows(unexpected),
        "sessions_with_pipeline_anomalies": _pipeline_anomaly_rows(successful),
        "failures_by_error_type": _failure_rows(failures),
        "requests_with_unavailable_token_usage": _missing_usage_rows(successful),
    }


def _unexpected_request_type_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = _group_rows(events, "request_type")
    for row in rows:
        row["reason"] = "outside_normal_three_pass_pipeline"
    return sorted(rows, key=lambda row: row["request_count"], reverse=True)


def _pipeline_anomaly_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normal_stage_set = set(NORMAL_ENGINE_STAGES)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        session_id = str(event.get("session_id") or "unknown")
        grouped[session_id].append(event)

    rows: list[dict[str, Any]] = []
    for session_id, items in grouped.items():
        stage_counts: dict[str, int] = defaultdict(int)
        unexpected_types = sorted(
            {str(event["request_type"]) for event in items if event["request_type"] not in normal_stage_set}
        )
        for event in items:
            request_type = str(event["request_type"])
            if request_type in normal_stage_set:
                stage_counts[request_type] += 1

        expected_count = max(stage_counts.values(), default=0)
        if expected_count == 0 and unexpected_types:
            expected_count = 1
        missing_stages = [
            stage for stage in NORMAL_ENGINE_STAGES if stage_counts.get(stage, 0) < expected_count
        ]
        duplicate_stages = [stage for stage, count in stage_counts.items() if count > expected_count]
        unbalanced_stages = len({stage_counts.get(stage, 0) for stage in NORMAL_ENGINE_STAGES}) > 1

        if not (unexpected_types or missing_stages or duplicate_stages or unbalanced_stages):
            continue

        latest_timestamp = max(event["timestamp"] for event in items)
        verticals = sorted({str(event.get("vertical") or "unknown") for event in items})
        rows.append(
            {
                "session_id": session_id,
                "timestamp": latest_timestamp.isoformat(),
                "date": latest_timestamp.date().isoformat(),
                "vertical": verticals[0] if len(verticals) == 1 else "mixed",
                "stage_counts": {stage: stage_counts.get(stage, 0) for stage in NORMAL_ENGINE_STAGES},
                "missing_stages": missing_stages,
                "unexpected_request_types": unexpected_types,
                "reason": _pipeline_anomaly_reason(missing_stages, unexpected_types, duplicate_stages),
                **_metric_row(items),
            }
        )
    return sorted(rows, key=lambda row: (row["date"], row["request_count"]), reverse=True)[:25]


def _pipeline_anomaly_reason(
    missing_stages: list[str], unexpected_types: list[str], duplicate_stages: list[str]
) -> str:
    reasons: list[str] = []
    if unexpected_types:
        reasons.append("unexpected_request_type")
    if missing_stages:
        reasons.append("missing_normal_stage")
    if duplicate_stages:
        reasons.append("duplicate_normal_stage")
    return ",".join(reasons) or "pipeline_stage_imbalance"


def _session_rows(
    events: list[dict[str, Any]], *, sort_by: str = "timestamp", direction: str = "desc"
) -> list[dict[str, Any]]:
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
                "timestamp": latest_timestamp.isoformat(),
                "date": latest_timestamp.date().isoformat(),
                "vertical": verticals[0] if len(verticals) == 1 else "mixed",
                "model": models[0] if len(models) == 1 else "mixed",
                "request_types": request_types,
                "stage_breakdown": _stage_breakdown_rows(items),
                **_metric_row(items),
            }
        )
    return sorted(rows, key=lambda row: row[sort_by], reverse=(direction == "desc"))


def _stage_breakdown_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[str(event.get("request_type") or "generation")].append(event)

    rows = []
    for stage, items in grouped.items():
        row = _metric_row(items)
        rows.append(
            {
                "stage": stage,
                "request_count": row["request_count"],
                "average_latency_ms": row["average_latency_ms"],
                "maximum_latency_ms": row["maximum_latency_ms"],
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
                "total_tokens": row["total_tokens"],
                "estimated_spend_usd": row["estimated_spend_usd"],
            }
        )
    return sorted(rows, key=lambda row: row["stage"])


def _resolve_report_range(
    start: datetime | None,
    end: datetime | None,
    reporting_window: str | None,
) -> tuple[datetime | None, datetime | None, str | None]:
    if reporting_window not in (None, "", DEFAULT_REPORTING_WINDOW):
        raise ValueError("unsupported reporting window")
    if start is None and end is None and reporting_window in (None, "", DEFAULT_REPORTING_WINDOW):
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=24)
        return start, end, DEFAULT_REPORTING_WINDOW
    return start, end, None


def _resolve_session_sort(sort_by: str, direction: str) -> tuple[str, str]:
    normalized_sort = str(sort_by or "timestamp")
    normalized_direction = str(direction or "desc").lower()
    if normalized_sort not in SESSION_SORT_FIELDS:
        raise ValueError("unsupported session sort")
    if normalized_direction not in {"asc", "desc"}:
        raise ValueError("unsupported session sort direction")
    return normalized_sort, normalized_direction


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
