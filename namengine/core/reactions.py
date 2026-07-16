"""Shared reaction handling for NamEngine results."""

from __future__ import annotations

from namengine.core.schemas import Reaction, ReactionValue


class ReactionError(ValueError):
    pass


PUBLIC_REACTION_VALUES = frozenset({ReactionValue.LOVE, ReactionValue.NO})


def build_reaction(session_id: str, result_id: str, value: str) -> Reaction:
    if not session_id:
        raise ReactionError("session_id is required")
    if not result_id:
        raise ReactionError("result_id is required")

    try:
        reaction_value = ReactionValue(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ReactionValue)
        raise ReactionError(f"reaction must be one of: {allowed}") from exc

    return Reaction(
        session_id=session_id,
        result_id=result_id,
        value=reaction_value,
    )


def build_public_reaction(session_id: str, result_id: str, value: str) -> Reaction:
    """Build a reaction accepted from a current customer-facing interface.

    ``build_reaction`` intentionally retains the durable three-value contract so
    historical ``maybe`` rows can still be deserialized, audited, and tested.
    New public submissions use this narrower entry point.
    """
    reaction = build_reaction(session_id, result_id, value)
    if reaction.value not in PUBLIC_REACTION_VALUES:
        allowed = ", ".join(item.value for item in (ReactionValue.LOVE, ReactionValue.NO))
        raise ReactionError(f"reaction must be one of: {allowed}")
    return reaction
