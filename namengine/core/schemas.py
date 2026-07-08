"""Shared data contract for the NamEngine platform.

These dataclasses define the durable shape of the naming product. Vertical apps
should adapt to this contract instead of each owning a separate result, taste,
reaction, share, and validation format.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReactionValue(str, Enum):
    LOVE = "love"
    MAYBE = "maybe"
    NO = "no"


class ValidationStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    UNKNOWN = "unknown"


class ModelProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    GROQ = "groq"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class Question:
    id: str
    label: str
    kind: str = "text"
    required: bool = False
    choices: tuple[str, ...] = ()
    placeholder: str = ""
    help_text: str = ""
    section: str = ""


@dataclass(frozen=True, slots=True)
class VerticalVisualConfig:
    audience: tuple[str, ...] = ()
    emotional_tone: tuple[str, ...] = ()
    main_colors: tuple[str, ...] = ()
    accent_colors: tuple[str, ...] = ()
    background_style: str = ""
    icon_style: str = ""
    illustration_style: str = ""
    hero_message: str = ""
    hero_support: str = ""
    identity_statement: str = ""
    identity_points: tuple[str, ...] = ()
    result_card_style: str = ""


@dataclass(frozen=True, slots=True)
class VerticalConfig:
    slug: str
    display_name: str
    object_label: str
    route_prefix: str
    intake_questions: tuple[Question, ...]
    prompt_context: str
    result_field_labels: dict[str, str] = field(default_factory=dict)
    validation_modules: tuple[str, ...] = ()
    theme: dict[str, str] = field(default_factory=dict)
    assets: dict[str, str] = field(default_factory=dict)
    visual: VerticalVisualConfig = field(default_factory=VerticalVisualConfig)
    default_result_count: int = 8


@dataclass(slots=True)
class NamingBrief:
    vertical: str
    inputs: dict[str, Any]
    liked_examples: list[str] = field(default_factory=list)
    rejected_examples: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(slots=True)
class ValidationResult:
    module: str
    status: ValidationStatus
    label: str
    message: str
    score: float | None = None
    source: str = ""
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NameResult:
    id: str
    name: str
    slug: str
    pronunciation: str = ""
    tagline: str = ""
    origin: str = ""
    meaning: str = ""
    why_this_name: str = ""
    fit_note: str = ""
    risks: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    validation: list[ValidationResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderResult:
    provider: ModelProvider
    names: list[NameResult] = field(default_factory=list)
    status: str = "ok"
    error: str = ""
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GenerationCandidate:
    result: NameResult
    provider: ModelProvider
    quality_score: float
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Reaction:
    session_id: str
    result_id: str
    value: ReactionValue
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class TasteProfile:
    session_id: str
    vertical: str
    loved_names: list[str] = field(default_factory=list)
    maybe_names: list[str] = field(default_factory=list)
    rejected_names: list[str] = field(default_factory=list)
    liked_sounds: list[str] = field(default_factory=list)
    disliked_sounds: list[str] = field(default_factory=list)
    style_preferences: dict[str, float] = field(default_factory=dict)
    rejected_lanes: list[str] = field(default_factory=list)
    summary: str = ""
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class RefinementRequest:
    session_id: str
    instruction: str
    reactions: list[Reaction] = field(default_factory=list)
    taste_profile: TasteProfile | None = None
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class NamingSession:
    id: str
    vertical: str
    brief: NamingBrief
    results: list[NameResult] = field(default_factory=list)
    reactions: list[Reaction] = field(default_factory=list)
    taste_profile: TasteProfile | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChosenName:
    id: str
    session_id: str
    result_id: str
    name: str
    vertical: str
    share_id: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


def to_plain_data(value: Any) -> Any:
    """Convert schema objects into JSON-friendly primitives."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: to_plain_data(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain_data(item) for item in value]
    return value
