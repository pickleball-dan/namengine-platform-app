# Figure 9 — Taste Engine Feedback Loop (Advanced Embodiment)

**Patent:** NamEngine Provisional Patent Application
**Figure:** 9 of 9
**Status:** Text specification — formal drawing required for non-provisional

## Description

Taste State architecture and Exploration Planner feedback loop across multiple generation rounds. Advanced embodiment. Shows Taste State initialization from CNI, Exploration Planner producing Exploration Strategy, generation and scoring under strategy, reaction capture, Evidence Extractor updating Taste State, and loop continuation.

## Text Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     ROUND 1                                 │
│                                                             │
│  [Intake] ──► [CNI Mapper] ──► [Taste State: initial]       │
│                                       │                     │
│                              [Exploration Planner]          │
│                              Reads: uncertainty,            │
│                              unexplored territories,        │
│                              confidence levels              │
│                                       │                     │
│                              [Exploration Strategy]         │
│                              • Target dimensions            │
│                              • Exploration ratio            │
│                              • Probe directives             │
│                                       │                     │
│                    ┌──────────────────┘                     │
│                    ▼                                        │
│  [Brief Constructor] ──► [Generation Router]                │
│                                  │                         │
│                         [Multi-Provider AI]                 │
│                                  │                         │
│                       [Quality Adapter Scoring]             │
│                       (Taste State + Exp. Strategy)         │
│                                  │                         │
│                      [Candidate Names → User]               │
│                                  │                         │
│                         [Reaction Capture]                  │
│                         • Like / Dislike                    │
│                         • Strong Like / Strong Dislike      │
│                                  │                         │
│                        [Evidence Extractor]                 │
│                         • Extract phonetic signals          │
│                         • Extract style/territory markers   │
│                         • Detect contradictions             │
│                                  │                         │
│                      [Taste State Update]                   │
│               (confidence, signals, contradictions,         │
│                unexplored territory map updated)            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     ROUND 2                                 │
│                                                             │
│         [Updated Taste State] ──► [Exploration Planner]     │
│         (higher confidence,           │                     │
│          resolved contradictions,     │                     │
│          narrowed uncertainty)   [New Exploration Strategy] │
│                                       │                     │
│                    ┌──────────────────┘                     │
│                    ▼                                        │
│  [Brief Constructor] ──► [Generation Router]                │
│  (excludes Round 1 names)       │                           │
│                        [Multi-Provider AI]                  │
│                                 │                           │
│                      [Quality Adapter Scoring]              │
│                      (enriched Taste State)                 │
│                                 │                           │
│                     [Candidate Names → User]                │
│                                 │                           │
│                 [Reaction Capture → Evidence → Update]      │
│                                 │                           │
│                    [Round 3 Exploration Planner...]         │
└─────────────────────────────────────────────────────────────┘
```

## Key Properties of the Loop

| Property | Description |
|---|---|
| Monotonically richer | Each round's Taste State is a superset of the prior round's |
| Adaptive strategy | Exploration Planner shifts exploration targets each round based on what was learned |
| Name exclusion | Previously presented names excluded from all rounds via session chain linkage |
| Weighted reactions | Strong reactions (heart/X) update Taste State with higher evidence weight than mild reactions |
| Explicit contradictions | Contradictory evidence stored explicitly, reduces confidence rather than being averaged away |
| Convergence | Taste State converges toward a precise model of the user's naming preferences over rounds |

## Taste State Fields (for illustrator reference)

| Field | Type | Description |
|---|---|---|
| preference_dimensions | dict | Named dimensions with inferred values |
| confidence_levels | dict | 0.0–1.0 float per dimension |
| uncertainty_flags | dict | Boolean per dimension |
| contradiction_records | list | Pairs of conflicting reaction signals |
| evidence_counters | dict | Confirming vs. disconfirming count per dimension |
| positive_signal_inventory | list | Phoneme patterns, style markers from liked names |
| negative_signal_inventory | list | Phoneme patterns, style markers from disliked names |
| unexplored_territory_map | dict | Dimensions not yet probed, prioritized for exploration |

## Notes for Patent Illustrator
- Two large round boxes stacked vertically (Round 1, Round 2), connected by arrow
- Round 1 starts with CNI → Taste State initialization
- Round 2 starts with Updated Taste State → Exploration Planner
- Both rounds share the same internal flow structure
- Evidence Extractor and Taste State Update should be clearly distinct steps
- Key properties table should appear as a caption or companion table
- This is the most important figure — allocate the most space
- Formal figure should use standard flowchart conventions (37 C.F.R. § 1.84)
