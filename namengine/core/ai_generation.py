"""AI-backed name generation with strict schema parsing and fallback safety."""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Callable
from typing import Any

import namengine.core.quality_adapters  # Registers built-in vertical adapters.
from namengine.core.prompt_versions import DEFAULT_PROMPT_VERSION, prompt_version_for
from namengine.core.quality_framework import (
    apply_quality_metadata,
    build_quality_taste_thesis,
    improve_quality_explanations,
    quality_model_score_keys,
    quality_prompt_guidance,
)
from namengine.core.schemas import (
    NameResult,
    NamingBrief,
    TasteProfile,
    VerticalConfig,
)
from namengine.core.validation import validate_results


DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_SECONDS = 24.0
PROMPT_VERSION = DEFAULT_PROMPT_VERSION
TASTE_STRATEGY_SCHEMA_NAME = "namengine_taste_strategy_v1"
NAME_GENERATION_SCHEMA_NAME = "namengine_name_generation_v1"


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
    """Generate names with NamEngine's LLM-first engine.

    NamEngine frames the user's intake, slider weights, and refinement context into
    one generation/ranking prompt. The LLM returns the top names plus audit context.
    """
    if not is_ai_generation_configured():
        raise AIGenerationError("OPENAI_API_KEY is not configured")

    target_count = count or _count_for_round(vertical, round_number)
    selected_model = model or os.getenv("NAMENGINE_OPENAI_MODEL", DEFAULT_MODEL)
    client = client_factory() if client_factory else None
    generation_id = f"gen-{uuid.uuid4().hex[:12]}"
    prompt_version = prompt_version_for(vertical.slug)

    taste_strategy = build_local_taste_strategy(
        vertical=vertical,
        brief=brief,
        round_number=round_number,
        taste_profile=taste_profile,
        previous_names=previous_names or [],
        count=target_count,
    )

    prompt = build_generation_prompt(
        vertical=vertical,
        brief=brief,
        round_number=round_number,
        taste_profile=taste_profile,
        previous_names=previous_names or [],
        count=target_count,
        taste_strategy=taste_strategy,
        prompt_version=prompt_version,
    )
    generation_call = _call_openai_with_metadata(
        prompt=prompt,
        model=selected_model,
        client_factory=(lambda: client) if client is not None else None,
        response_format=name_generation_response_format(vertical.slug),
    )
    generation_audit = parse_generation_audit_response(generation_call["text"])
    results = parse_ai_generation_response(generation_call["text"], vertical.slug)
    if not results:
        raise AIGenerationError("AI generation returned no usable names")

    selected_results = results[: prompt["count"]]
    improve_quality_explanations(vertical.slug, selected_results, brief)
    validated = validate_results(vertical, brief, selected_results)
    apply_quality_metadata(vertical.slug, validated, brief)
    from namengine.core.intake import version_metadata_for_brief

    intake_metadata = version_metadata_for_brief(brief)
    for result in validated:
        result.metadata.update(intake_metadata)
        result.metadata["taste_strategy"] = taste_strategy
        result.metadata["engine_pipeline"] = "weighted_prompt_v1+candidate_ranker_v1"
        result.metadata["prompt_version"] = prompt_version
        result.metadata["generation_id"] = generation_id
        result.metadata["model"] = selected_model
        result.metadata["candidate_pool"] = generation_audit["candidate_pool"]
        result.metadata["rejected_candidates"] = generation_audit["rejected_candidates"]
        result.metadata["ai_calls"] = [
            _call_audit_summary(
                "candidate_generator_ranker_v1",
                generation_call,
                prompt,
                prompt_version,
            ),
        ]
    return validated


def build_local_taste_strategy(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_profile: TasteProfile | None = None,
    previous_names: list[str] | None = None,
    count: int | None = None,
) -> dict[str, Any]:
    """Create the naming strategy locally so production needs only one LLM call."""
    inputs = brief.inputs
    cultural_heritage = str(inputs.get("cultural_heritage") or "No preference").strip()
    style = str(inputs.get("style") or "").strip()
    sound = str(inputs.get("sound") or "").strip()
    discovery = str(inputs.get("discovery_style") or "").strip()
    familiarity = str(inputs.get("familiarity_preference") or "").strip()
    weighting = _taste_weighting_payload(brief)
    target_count = count or _count_for_round(vertical, round_number)
    prior_summary = taste_profile.summary if taste_profile else ""
    previous = previous_names or []

    taste_thesis = build_quality_taste_thesis(vertical.slug, brief, weighting)
    if taste_thesis is None:
        thesis_parts = [
            part
            for part in [style, sound, cultural_heritage]
            if part and part.lower() != "no preference"
        ]
        taste_thesis = " / ".join(thesis_parts) if thesis_parts else vertical.prompt_context
    return {
        "taste_thesis": taste_thesis,
        "primary_priorities": [
            f"Return exactly {target_count} strong final names.",
            "Use the intake and slider weights to shape the prompt tradeoffs.",
            "Make meaning, vibe, cultural fit, sound, and family usability visible in the final choices.",
            "Avoid repeating previous names and avoid generic filler.",
        ],
        "avoidance_rules": [
            "Do not use local candidate pools as the source of names.",
            "Do not drift away from a requested cultural heritage just to satisfy style.",
            "Do not return names that conflict with the avoid list or previous names.",
        ],
        "slider_weighting": weighting,
        "style_direction": style,
        "sound_direction": sound,
        "discovery_direction": discovery,
        "familiarity_direction": familiarity,
        "cultural_heritage": cultural_heritage,
        "prior_taste_summary": prior_summary,
        "previous_names": previous,
    }


def build_taste_interpreter_prompt(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_profile: TasteProfile | None,
    previous_names: list[str],
    count: int,
) -> dict[str, Any]:
    """Build the first-stage prompt that translates inputs into naming strategy."""
    return {
        "role": "NamEngine chief taste interpreter",
        "engine_stage": "taste_interpreter_v1",
        "vertical": vertical.slug,
        "vertical_context": vertical.prompt_context,
        "round_number": round_number,
        "target_final_count": count,
        "mission": (
            "Interpret the user's taste before generating names. Do not produce final names. "
            "Turn form choices, user-written text, Feelings Scale strengths, avoid-list items, "
            "and prior reactions into a practical naming strategy."
        ),
        "brief": {
            "inputs": brief.inputs,
            "avoid": brief.avoid,
            "notes": brief.notes,
            "liked_examples": brief.liked_examples,
            "rejected_examples": brief.rejected_examples,
        },
        "taste_profile": _taste_profile_payload(taste_profile),
        "taste_weighting": _taste_weighting_payload(brief),
        "previous_names": previous_names,
        "interpretation_rules": {
            "user_written_text_is_first_class_signal": True,
            "feelings_scale_changes_strategy_not_just_order": True,
            "use_slider_weights_to_prioritize_prompt_tradeoffs": True,
            "hard_constraints": ["avoid exact avoid-list matches", "avoid repeats", "respect vertical safety checks"],
            "explain_tradeoffs_internally": True,
            "do_not_generate_final_names": True,
        },
        "output_contract": {
            "format": "json",
            "required_fields": [
                "taste_thesis",
                "priority_interpretation",
                "hard_constraints",
                "soft_preferences",
                "anti_patterns",
                "naming_territories",
                "candidate_rubric",
                "diversity_plan",
            ],
            "naming_territories_item_fields": ["label", "description", "example_style", "risk"],
            "candidate_rubric_item_fields": ["criterion", "weight", "what_good_looks_like"],
        },
    }


def taste_strategy_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": TASTE_STRATEGY_SCHEMA_NAME,
        "description": "NamEngine taste interpretation strategy before candidate generation.",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "taste_thesis",
                "priority_interpretation",
                "hard_constraints",
                "soft_preferences",
                "anti_patterns",
                "naming_territories",
                "candidate_rubric",
                "diversity_plan",
            ],
            "properties": {
                "taste_thesis": {"type": "string"},
                "priority_interpretation": {"type": "string"},
                "hard_constraints": {"type": "array", "items": {"type": "string"}},
                "soft_preferences": {"type": "array", "items": {"type": "string"}},
                "anti_patterns": {"type": "array", "items": {"type": "string"}},
                "naming_territories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["label", "description", "example_style", "risk"],
                        "properties": {
                            "label": {"type": "string"},
                            "description": {"type": "string"},
                            "example_style": {"type": "string"},
                            "risk": {"type": "string"},
                        },
                    },
                },
                "candidate_rubric": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["criterion", "weight", "what_good_looks_like"],
                        "properties": {
                            "criterion": {"type": "string"},
                            "weight": {"type": "number"},
                            "what_good_looks_like": {"type": "string"},
                        },
                    },
                },
                "diversity_plan": {"type": "string"},
            },
        },
    }


def build_generation_prompt(
    vertical: VerticalConfig,
    brief: NamingBrief,
    round_number: int,
    taste_profile: TasteProfile | None,
    previous_names: list[str],
    count: int,
    taste_strategy: dict[str, Any] | None = None,
    prompt_version: str | None = None,
) -> dict[str, Any]:
    round_goal = {
        1: "Discovery: explore strong but varied naming lanes.",
        2: "Refined: move closer to the user's taste using reactions.",
        3: "Finalists: produce the most choose-worthy names only.",
    }.get(round_number, "One more specific round: respond narrowly to the user's latest direction.")

    return {
        "role": "NamEngine senior naming strategist",
        "engine_stage": "candidate_generator_ranker_v1",
        "prompt_version": prompt_version
        or prompt_version_for(vertical.slug),
        "vertical": vertical.slug,
        "vertical_context": vertical.prompt_context,
        "round_number": round_number,
        "round_goal": round_goal,
        "count": count,
        "mission": (
            "Generate a broader internal candidate pool, judge it against the taste strategy, "
            "reject weak or redundant options, then return both the audit trail and only the strongest final names."
        ),
        "brief": {
            "inputs": brief.inputs,
            "avoid": brief.avoid,
            "notes": brief.notes,
            "liked_examples": brief.liked_examples,
            "rejected_examples": brief.rejected_examples,
        },
        "taste_strategy": taste_strategy or {},
        "taste_profile": _taste_profile_payload(taste_profile),
        "taste_weighting": _taste_weighting_payload(brief),
        "previous_names": previous_names,
        "generation_rules": {
            "generate_more_candidates_than_final_count_internally": True,
            "target_internal_candidate_pool": count,
            "show_only_final_count": count,
            "return_candidate_pool_and_rejected_candidates": False,
            "rejected_candidates_must_explain_why_they_lost": False,
            "user_written_text_must_change_candidate_choice_when_specific": True,
            "feelings_scale_priority_must_be_visible_in_name_choice_and_rationale": True,
            "weight_final_selection_according_to_slider_priorities": True,
            "avoid_generic_ai_name_lists": True,
            "prefer_names_that_can_survive_real_world_use": True,
            "llm_is_creative_source_not_local_pool": True,
            "do_not_limit_candidates_to_any_preexisting_app_list": True,
        },
        "baby_generation_guidance": _baby_generation_guidance(vertical, brief),
        "diversity_rules": {
            "do_not_repeat_previous_names": True,
            "treat_previous_names_as_hard_exclusions": True,
            "avoid_close_variants_of_previous_names": True,
            "broaden_style_origin_and_sound_lanes_after_round_one": round_number >= 2,
            "avoid_eight_names_from_the_same_sound_or_style_lane": True,
        },
        "validation_expectations": list(vertical.validation_modules),
        "output_contract": {
            "format": "json",
            "top_level_keys": ["names"],
            "required_fields": [
                "name",
                "pronunciation",
                "tagline",
                "origin",
                "meaning",
                "why_this_name",
                "fit_note",
                "risks",
                "tags",
                "scores",
            ],
            "score_keys": _score_keys(vertical.slug),
            "metadata_guidance": _explanation_guidance(vertical.slug),
        },
    }


def _taste_weighting_payload(brief: NamingBrief) -> dict[str, Any]:
    weights: dict[str, int] = {}
    for key, value in brief.inputs.items():
        if not str(key).startswith("taste_strength_"):
            continue
        section = str(key)[len("taste_strength_") :].replace("_", " ").strip()
        try:
            score = int(float(value))
        except (TypeError, ValueError):
            continue
        weights[section or key] = max(0, min(100, score))

    if not weights:
        return {
            "has_slider_weights": False,
            "instruction": "No explicit slider weights were supplied; balance all intake signals normally.",
        }

    ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    return {
        "has_slider_weights": True,
        "weights_0_to_100": dict(ranked),
        "strongest_signal": ranked[0][0],
        "instruction": (
            "Use these slider weights as prompt priorities: higher-weighted sections should shape the final 8 names, "
            "the rationale, and the rejection tradeoffs more strongly than lower-weighted sections. Do not ignore low-weighted "
            "sections; treat them as secondary constraints."
        ),
    }


def _baby_generation_guidance(vertical: VerticalConfig, brief: NamingBrief) -> dict[str, Any]:
    if vertical.slug != "baby":
        return {}

    cultural_heritage = str(brief.inputs.get("cultural_heritage") or "").strip()
    cultural_context = str(brief.inputs.get("cultural_context") or "").strip()
    style = str(brief.inputs.get("style") or "").strip()
    guidance: dict[str, Any] = {
        "meaning_and_vibe_are_first_class": True,
        "names_should_feel_like_human_curation_not_database_lookup": True,
        "include_origin_or_language_context_in_origin_field": True,
        "meaning_field_should_be_specific_when_known": True,
        "tagline_should_capture_emotional_vibe": True,
        "why_this_name_should_connect_style_heritage_sound_and_family_context": True,
    }
    if cultural_heritage and cultural_heritage.lower() not in {"no preference", "none"}:
        guidance.update(
            {
                "cultural_heritage_is_primary_creative_source": cultural_heritage,
                "generate_authentic_culturally_grounded_options": True,
                "avoid_generic_names_that_only_match_style": True,
                "consider_modern_traditional_rare_and_easy_to_pronounce_lanes": True,
                "do_not_stop_after_obvious_or_overused_examples": True,
                "if_relevant_include_script_or_transliteration_in_origin_or_meaning": True,
                "final_list_should_show_breadth_within_the_heritage_not_breadth_away_from_it": True,
            }
        )
    if cultural_context:
        guidance["additional_cultural_context"] = cultural_context
    if style:
        guidance["style_signal"] = style
    return guidance


def name_generation_response_format(vertical_slug: str | None = None) -> dict[str, Any]:
    score_keys = _score_keys(vertical_slug or "")
    return {
        "type": "json_schema",
        "name": NAME_GENERATION_SCHEMA_NAME,
        "description": "NamEngine final ranked naming results.",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["names"],
            "properties": {
                "names": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "name",
                            "pronunciation",
                            "tagline",
                            "origin",
                            "meaning",
                            "why_this_name",
                            "fit_note",
                            "risks",
                            "tags",
                            "scores",
                        ],
                        "properties": {
                            "name": {"type": "string"},
                            "pronunciation": {"type": "string"},
                            "tagline": {"type": "string"},
                            "origin": {"type": "string"},
                            "meaning": {"type": "string"},
                            "why_this_name": {"type": "string"},
                            "fit_note": {"type": "string"},
                            "risks": {"type": "array", "items": {"type": "string"}},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "scores": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": score_keys,
                                "properties": {
                                    key: {"type": "number"} for key in score_keys
                                },
                            },
                        },
                    },
                }
            },
        },
    }


def _score_keys(vertical_slug: str) -> list[str]:
    return list(
        quality_model_score_keys(vertical_slug, ("callability", "warmth", "distinctiveness"))
    )


def _explanation_guidance(vertical_slug: str) -> list[str]:
    guidance = [
        "Return only the final names array; do not include candidate_pool or rejected_candidates in the live response",
        "why_this_name should explain why this name won against the user's taste thesis",
        "fit_note should connect to a concrete user input, not generic praise",
        "risks should be honest and practical",
    ]
    return guidance + list(quality_prompt_guidance(vertical_slug, ()))

def parse_taste_strategy_response(raw_text: str) -> dict[str, Any]:
    payload = _loads_json_payload(raw_text)
    if not isinstance(payload, dict):
        raise AIGenerationError("Taste strategy response was not a JSON object")

    required = {
        "taste_thesis",
        "priority_interpretation",
        "hard_constraints",
        "soft_preferences",
        "anti_patterns",
        "naming_territories",
        "candidate_rubric",
        "diversity_plan",
    }
    missing = sorted(key for key in required if key not in payload)
    if missing:
        raise AIGenerationError(f"Taste strategy response missing fields: {', '.join(missing)}")

    return {
        "taste_thesis": str(payload.get("taste_thesis", "")).strip(),
        "priority_interpretation": str(payload.get("priority_interpretation", "")).strip(),
        "hard_constraints": _string_list(payload.get("hard_constraints")),
        "soft_preferences": _string_list(payload.get("soft_preferences")),
        "anti_patterns": _string_list(payload.get("anti_patterns")),
        "naming_territories": _dict_list(payload.get("naming_territories")),
        "candidate_rubric": _dict_list(payload.get("candidate_rubric")),
        "diversity_plan": str(payload.get("diversity_plan", "")).strip(),
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


def parse_generation_audit_response(raw_text: str) -> dict[str, list[dict[str, Any]]]:
    payload = _loads_json_payload(raw_text)
    if not isinstance(payload, dict):
        return {"candidate_pool": [], "rejected_candidates": []}
    return {
        "candidate_pool": _dict_list(payload.get("candidate_pool")),
        "rejected_candidates": _dict_list(payload.get("rejected_candidates")),
    }


def _call_openai(
    prompt: dict[str, Any],
    model: str,
    client_factory: Callable[[], Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> str:
    return _call_openai_with_metadata(
        prompt=prompt,
        model=model,
        client_factory=client_factory,
        response_format=response_format,
    )["text"]


def _call_openai_with_metadata(
    prompt: dict[str, Any],
    model: str,
    client_factory: Callable[[], Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        client = client_factory() if client_factory else _default_client()
        kwargs = {
            "model": model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are NamEngine, an expert naming strategist. "
                        "Follow the supplied structured output schema exactly."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=True),
                },
            ],
            "temperature": 0.75,
            "timeout": _openai_timeout_seconds(),
            "max_output_tokens": _openai_max_output_tokens(),
        }
        if response_format is not None:
            kwargs["text"] = {"format": response_format}
        response = client.responses.create(**kwargs)
    except Exception as exc:  # pragma: no cover - live SDK/network behavior
        raise AIGenerationError(str(exc)) from exc

    text = getattr(response, "output_text", "")
    if text:
        return {
            "text": str(text),
            "model": model,
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "usage": _usage_payload(getattr(response, "usage", None)),
            "schema_name": response_format.get("name") if response_format else None,
        }
    raise AIGenerationError("OpenAI response did not include output_text")


def _call_audit_summary(
    stage: str,
    call: dict[str, Any],
    prompt: dict[str, Any],
    prompt_version: str = PROMPT_VERSION,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "model": call.get("model"),
        "latency_ms": call.get("latency_ms"),
        "usage": call.get("usage") or {},
        "prompt_version": prompt_version,
        "schema_name": call.get("schema_name"),
        "prompt": prompt,
    }


def _usage_payload(usage: Any) -> dict[str, int]:
    if usage is None:
        return {}
    payload: dict[str, int] = {}
    aliases = {
        "input_tokens": ("input_tokens", "prompt_tokens"),
        "output_tokens": ("output_tokens", "completion_tokens"),
        "total_tokens": ("total_tokens",),
    }
    for canonical, names in aliases.items():
        for name in names:
            value = getattr(usage, name, None)
            if value is None and isinstance(usage, dict):
                value = usage.get(name)
            if isinstance(value, int):
                payload[canonical] = value
                break
    return payload


def _default_client():
    from openai import OpenAI

    return OpenAI(max_retries=0)


def _openai_timeout_seconds() -> float:
    raw_value = os.getenv("NAMENGINE_OPENAI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        value = float(raw_value)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return max(1.0, value)


def _openai_max_output_tokens() -> int:
    raw_value = os.getenv("NAMENGINE_OPENAI_MAX_OUTPUT_TOKENS", "2600")
    try:
        value = int(raw_value)
    except ValueError:
        return 2600
    return max(1000, value)


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


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            rows.append({str(key): item[key] for key in item})
    return rows


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
