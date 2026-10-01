"""Shared journey lifecycle decisions for NamEngine routes and templates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from namengine.core.schemas import VerticalConfig


@dataclass(frozen=True, slots=True)
class JourneyLifecycle:
    """Authoritative action policy for one naming journey state."""

    vertical: VerticalConfig
    snapshot: dict[str, Any] | None = None
    paid_access: bool = False
    min_reactions_for_refinement: int = 3

    @property
    def round_number(self) -> int:
        if self.snapshot is None:
            return 1
        try:
            return int(self.snapshot.get("session", {}).get("round_number") or 1)
        except (TypeError, ValueError):
            return 1

    @property
    def result_count(self) -> int:
        if self.snapshot is None:
            return 0
        return len(self.snapshot.get("results") or [])

    @property
    def is_terminal(self) -> bool:
        return self.round_number >= max(1, int(self.vertical.max_rounds or 1))

    @property
    def is_final_decision_mode(self) -> bool:
        return self.is_terminal and self.vertical.terminal_reaction_mode == "love_only"

    @property
    def project_complete(self) -> bool:
        return self.paid_access and self.is_terminal

    def can_generate_first_list(self) -> bool:
        return self.snapshot is None or self.round_number == 1

    def can_enter_review(self) -> bool:
        return self.vertical.review_mode == "direction_review" and self.can_edit_direction()

    def can_edit_direction(self) -> bool:
        return not (
            self.paid_access
            and self.is_terminal
            and self.vertical.terminal_edit_locked
        )

    def can_refine(self) -> bool:
        return not self.is_terminal

    def can_react(self, value: str) -> bool:
        if self.is_terminal and self.vertical.terminal_reaction_mode == "love_only":
            return value == "love"
        return True

    def can_compare(self) -> bool:
        return self.paid_access and self.snapshot is not None

    def can_choose(self) -> bool:
        return self.paid_access and self.snapshot is not None

    def can_share(self) -> bool:
        return self.paid_access and self.snapshot is not None

    def can_save_resume(self) -> bool:
        return self.snapshot is not None

    def can_start_new_journey(
        self,
        *,
        existing_session_id: str = "",
        requested_session_id: str = "",
    ) -> bool:
        if not self.paid_access or not existing_session_id:
            return True
        return existing_session_id == requested_session_id


def build_journey_lifecycle(
    vertical: VerticalConfig,
    snapshot: dict[str, Any] | None = None,
    *,
    paid_access: bool = False,
    min_reactions_for_refinement: int = 3,
) -> JourneyLifecycle:
    return JourneyLifecycle(
        vertical=vertical,
        snapshot=snapshot,
        paid_access=paid_access,
        min_reactions_for_refinement=min_reactions_for_refinement,
    )
