"""Provider performance analytics from persisted user behavior."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProviderPerformance:
    provider: str
    vertical: str
    generated_count: int = 0
    love_count: int = 0
    maybe_count: int = 0
    no_count: int = 0
    chosen_count: int = 0
    quality_score_total: float = 0.0
    result_ids: list[str] = field(default_factory=list)

    @property
    def reaction_count(self) -> int:
        return self.love_count + self.maybe_count + self.no_count

    @property
    def average_quality_score(self) -> float:
        if self.generated_count == 0:
            return 0.0
        return round(self.quality_score_total / self.generated_count, 3)

    @property
    def love_rate(self) -> float:
        if self.reaction_count == 0:
            return 0.0
        return round(self.love_count / self.reaction_count, 3)

    @property
    def choose_rate(self) -> float:
        if self.generated_count == 0:
            return 0.0
        return round(self.chosen_count / self.generated_count, 3)

    @property
    def performance_score(self) -> float:
        return round(
            (self.average_quality_score * 0.35)
            + (self.love_rate * 0.35)
            + (self.choose_rate * 0.3),
            3,
        )

    def to_row(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "vertical": self.vertical,
            "generated_count": self.generated_count,
            "love_count": self.love_count,
            "maybe_count": self.maybe_count,
            "no_count": self.no_count,
            "chosen_count": self.chosen_count,
            "average_quality_score": self.average_quality_score,
            "love_rate": self.love_rate,
            "choose_rate": self.choose_rate,
            "performance_score": self.performance_score,
            "metadata": {"result_ids": self.result_ids},
        }


def build_provider_performance(snapshot: dict[str, Any]) -> list[ProviderPerformance]:
    session = snapshot["session"]
    vertical = str(session["vertical"])
    reactions_by_result = {
        row["result_id"]: row["value"]
        for row in snapshot.get("reactions", [])
    }
    chosen_result_ids = {
        row["result_id"]
        for row in snapshot.get("chosen_names", [])
    }
    by_provider: dict[str, ProviderPerformance] = {}

    for row in snapshot.get("results", []):
        result = json.loads(row["result_json"])
        metadata = result.get("metadata", {})
        provider = str(metadata.get("provider") or metadata.get("source") or "unknown")
        performance = by_provider.setdefault(
            provider,
            ProviderPerformance(provider=provider, vertical=vertical),
        )
        performance.generated_count += 1
        performance.result_ids.append(str(row["id"]))
        performance.quality_score_total += _quality_score(result)

        reaction = reactions_by_result.get(row["id"])
        if reaction == "love":
            performance.love_count += 1
        elif reaction == "maybe":
            performance.maybe_count += 1
        elif reaction == "no":
            performance.no_count += 1

        if row["id"] in chosen_result_ids:
            performance.chosen_count += 1

    return sorted(
        by_provider.values(),
        key=lambda item: item.performance_score,
        reverse=True,
    )


def _quality_score(result: dict[str, Any]) -> float:
    metadata = result.get("metadata", {})
    if isinstance(metadata.get("quality_score"), (int, float)):
        return float(metadata["quality_score"])

    scores = result.get("scores", {})
    if not isinstance(scores, dict):
        return 0.0
    parts = [
        float(scores.get("callability", 0.0)),
        float(scores.get("warmth", 0.0)),
        float(scores.get("distinctiveness", 0.0)),
    ]
    return sum(parts) / len(parts)
