"""Best-effort, privacy-preserving telemetry for OpenAI calls."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def usage_fields(usage: Any) -> dict[str, int | None]:
    return {
        "input_tokens": _value(usage, "input_tokens"),
        "output_tokens": _value(usage, "output_tokens", _value(usage, "completion_tokens")),
        "total_tokens": _value(usage, "total_tokens"),
    }


def record_openai_telemetry(
    *,
    request_type: str,
    model: str | None,
    started_at: float,
    success: bool,
    usage: Any = None,
    image_count: int | None = None,
    image_size: str | None = None,
    context: str | None = None,
    error_type: str | None = None,
) -> None:
    """Append a small JSONL event; all telemetry failures are swallowed."""
    try:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_type": request_type,
            "model": model,
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 1),
            "success": bool(success),
            **usage_fields(usage),
        }
        if image_count is not None:
            event["image_count"] = image_count
        if image_size is not None:
            event["image_size"] = image_size
        if context:
            event["context"] = context
        if error_type:
            event["error_type"] = error_type
        target = os.getenv("NAMENGINE_OPENAI_TELEMETRY_PATH", "")
        if not target:
            return
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    except Exception:
        return
