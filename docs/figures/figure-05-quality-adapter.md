# Figure 5 — Quality Adapter Architecture

**Patent:** NamEngine Provisional Patent Application
**Figure:** 5 of 9
**Status:** Text specification — formal drawing required for non-provisional

## Description

Quality adapter architecture: vertical-specific score dimensions, dimension weights summing to 1.0, model score keys, taste thesis builder, and explanation improvement hooks.

## Text Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                  QUALITY ADAPTER (Baby vertical example)     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  INPUT: Candidate Name + NamingBrief + TasteProfile          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              TASTE THESIS BUILDER                   │    │
│  │  Reads priority_weights + taste profile             │    │
│  │  Constructs AI scoring prompt directives:           │    │
│  │  • "Prioritize classic style (weight: 0.6)"         │    │
│  │  • "Soft phonetics are important (weight: 0.3)"     │    │
│  │  • Positive examples: [liked names from profile]    │    │
│  │  • Negative examples: [disliked names from profile] │    │
│  └──────────────────────────┬──────────────────────────┘    │
│                             │                                │
│                             ▼                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            SCORING DIMENSIONS (Baby)                │    │
│  │                                                     │    │
│  │  Dimension           Base Weight  Priority Adjusted │    │
│  │  ─────────────────   ──────────   ────────────────  │    │
│  │  Style alignment     0.30         × priority_weight │    │
│  │  Phonetic fit        0.25         × priority_weight │    │
│  │  Distinctiveness     0.20         × priority_weight │    │
│  │  Cultural fit        0.15         × priority_weight │    │
│  │  Emotional quality   0.10         × priority_weight │    │
│  │                      ──────                         │    │
│  │  Total               1.00                           │    │
│  └──────────────────────────┬──────────────────────────┘    │
│                             │                                │
│                             ▼                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         COMPOSITE SCORE + EXPLANATION               │    │
│  │  score: 0.0–1.0 float                               │    │
│  │  rationale: per-dimension breakdown                 │    │
│  │  improvement_hooks: suggestions for next round      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  OUTPUT: Ranked candidates with scores and rationales        │
└──────────────────────────────────────────────────────────────┘
```

## Notes for Patent Illustrator
- Three-tier internal structure: Taste Thesis Builder → Scoring Dimensions → Output
- Show dimension weight table as an actual table in the figure
- Highlight that weights are adjusted by priority_weights (dynamic, not fixed)
- Each vertical (Baby/Pet/Business) has its own adapter with different dimensions
- Formal figure should use standard block diagram conventions (37 C.F.R. § 1.84)
