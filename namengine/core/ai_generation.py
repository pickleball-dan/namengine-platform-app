"""AI-backed name generation with strict schema parsing and fallback safety."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from namengine.core.schemas import (
    NameResult,
    NamingBrief,
    TasteProfile,
    VerticalConfig,
)
from namengine.core.validation import validate_results


DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_SECONDS = 8.0


class AIGenerationError(RuntimeError):
    pass


def is_ai_generation_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def generate_ai_names(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_profile: TasteProfile | None = None,
    previous_names: list[str] | None = None,
    count: int | None = None,
    model: str | None = None,
    client_factory: Callable[[], Any] | None = None,
) -> list[NameResult]:
    if not is_ai_generation_configured():
        raise AIGenerationError("OPENAI_API_KEY is not configured")

    prompt = build_generation_prompt(
        vertical=vertical,
        brief=brief,
        round_number=round_number,
        taste_profile=taste_profile,
        previous_names=previous_names or [],
        count=count or _count_for_round(vertical, round_number),
    )
    raw_text = _call_openai(
        prompt=prompt,
        model=model or os.getenv("NAMENGINE_OPENAI_MODEL", DEFAULT_MODEL),
        client_factory=client_factory,
    )
    results = parse_ai_generation_response(raw_text, vertical.slug)
    if not results:
        raise AIGenerationError("AI generation returned no usable names")
    return validate_results(vertical, brief, results[: prompt["count"]])


def build_generation_prompt(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_profile: TasteProfile | None,
    previous_names: list[str],
    count: int,
) -> dict[str, Any]:
    round_goal = {
        1: "Discovery: explore strong but varied naming lanes.",
        2: "Refined: move closer to the user's taste using reactions.",
        3: "Finalists: produce the most choose-worthy names only.",
    }.get(round_number, "One more specific round: respond narrowly to the user's latest direction.")

    return {
        "role": "NamEngine senior naming strategist",
        "vertical": vertical.slug,
        "vertical_context": vertical.prompt_context,
        "round_number": round_number,
        "round_goal": round_goal,
        "count": count,
        "brief": {
            "inputs": brief.inputs,
            "avoid": brief.avoid,
            "notes": brief.notes,
            "liked_examples": brief.liked_examples,
            "rejected_examples": brief.rejected_examples,
        },
        "taste_profile": _taste_profile_payload(taste_profile),
        "previous_names": previous_names,
        "validation_expectations": list(vertical.validation_modules),
        "output_contract": {
            "format": "json",
            "top_level_key": "names",
            "required_fields": [
                "name",
                "pronunciation",
                "tagline",
                "meaning",
                "why_this_name",
                "fit_note",
                "risks",
                "tags",
                "scores",
            ],
            "score_keys": ["callability", "warmth", "distinctiveness"],
        },
    }


def parse_ai_generation_response(raw_text: str, vertical_slug: str) -> list[NameResult]:
    payload = _loads_json_payload(raw_text)
    rows = payload.get("names", payload if isinstance(payload, list) else [])
    if not isinstance(rows, list):
        raise AIGenerationError("AI response did not contain a names list")

    results: list[NameResult] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result_id = f"{vertical_slug}-{len(results) + 1}"
        results.append(
            NameResult(
                id=result_id,
                name=name,
                slug=_slugify(name),
                pronunciation=str(row.get("pronunciation", "")).strip(),
                tagline=str(row.get("tagline", "")).strip(),
                origin=str(row.get("origin", "")).strip(),
                meaning=str(row.get("meaning", "")).strip(),
                why_this_name=str(row.get("why_this_name", "")).strip(),
                fit_note=str(row.get("fit_note", "")).strip(),
                risks=_string_list(row.get("risks")),
                tags=_string_list(row.get("tags")),
                scores=_scores(row.get("scores")),
                metadata={"source": "openai"},
            )
        )
    return results


def _call_openai(
    prompt: dict[str, Any],
    model: str,
    client_factory: Callable[[], Any] | None = None,
) -> str:
    try:
        client = client_factory() if client_factory else _default_client()
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are NamEngine, an expert naming strategist. "
                        "Return only valid JSON. Do not include markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=True),
                },
            ],
            temperature=0.9,
            timeout=_openai_timeout_seconds(),
        )
    except Exception as exc:  # pragma: no cover - live SDK/network behavior
        raise AIGenerationError(str(exc)) from exc

    text = getattr(response, "output_text", "")
    if text:
        return str(text)
    raise AIGenerationError("OpenAI response did not include output_text")


def _default_client():
    from openai import OpenAI

    return OpenAI()


def _openai_timeout_seconds() -> float:
    raw_value = os.getenv("NAMENGINE_OPENAI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        value = float(raw_value)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return max(1.0, value)


def _loads_json_payload(raw_text: str) -> Any:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIGenerationError("AI response was not valid JSON") from exc


def _taste_profile_payload(profile: TasteProfile | None) -> dict[str, Any]:
    if profile is None:
        return {}
    return {
        "summary": profile.summary,
        "loved_names": profile.loved_names,
        "maybe_names": profile.maybe_names,
        "rejected_names": profile.rejected_names,
        "liked_sounds": profile.liked_sounds,
        "disliked_sounds": profile.disliked_sounds,
        "style_preferences": profile.style_preferences,
        "rejected_lanes": profile.rejected_lanes,
    }


def _count_for_round(vertical: VerticalConfig, round_number: int) -> int:
    if round_number >= 3:
        return 6
    return vertical.default_result_count


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _scores(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    scores: dict[str, float] = {}
    for key, item in value.items():
        if isinstance(item, (int, float)):
            scores[str(key)] = max(0.0, min(float(item), 1.0))
    return scores


def _slugify(value: str) -> str:
    import re

    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return clean or "name"
