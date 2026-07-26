"""Estimated API cost helpers for Mission Control telemetry."""

from __future__ import annotations

from typing import Any


MODEL_RATES_PER_MILLION_TOKENS = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
}


def estimate_ai_calls_cost_usd(
    calls: list[Any],
    *,
    fallback_model: str = "",
) -> dict[str, Any]:
    """Estimate total text-generation API cost from persisted call telemetry."""
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "pricing_models": [],
    }
    pricing_models: set[str] = set()
    for call in calls:
        estimate = estimate_ai_call_cost_usd(call, fallback_model=fallback_model)
        if estimate is None:
            continue
        totals["input_tokens"] += estimate["input_tokens"]
        totals["output_tokens"] += estimate["output_tokens"]
        totals["total_tokens"] += estimate["total_tokens"]
        totals["estimated_cost_usd"] += estimate["estimated_cost_usd"]
        pricing_models.add(estimate["pricing_model"])
    totals["estimated_cost_usd"] = round(float(totals["estimated_cost_usd"]), 6)
    totals["pricing_models"] = sorted(pricing_models)
    return totals


def estimate_ai_call_cost_usd(
    call: Any,
    *,
    fallback_model: str = "",
) -> dict[str, Any] | None:
    if not isinstance(call, dict):
        return None
    usage = call.get("usage") if isinstance(call.get("usage"), dict) else {}
    input_tokens = _safe_int(usage.get("input_tokens"))
    output_tokens = _safe_int(usage.get("output_tokens"))
    total_tokens = _safe_int(usage.get("total_tokens")) or input_tokens + output_tokens
    model = _normalize_model(str(call.get("model") or fallback_model or ""))
    rates = MODEL_RATES_PER_MILLION_TOKENS.get(model)
    if rates is None:
        return None
    estimated_cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(estimated_cost, 6),
        "pricing_model": model,
    }


def _normalize_model(model: str) -> str:
    normalized = model.strip().lower()
    if normalized.startswith("openai/"):
        normalized = normalized.split("/", 1)[1]
    return normalized


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
