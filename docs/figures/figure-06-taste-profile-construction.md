# Figure 6 — Taste Profile Construction

**Patent:** NamEngine Provisional Patent Application
**Figure:** 6 of 9
**Status:** Text specification — formal drawing required for non-provisional

## Description

Taste profile construction from session reaction chain: phonetic signal extraction, territory and rationale aggregation, style scoring by tag, rejected lane tracking, and profile serialization.

## Text Diagram

```
     [Session Chain: Round 1 reactions + Round 2 reactions + ...]
                              │
                              ▼
          ┌───────────────────────────────────┐
          │      TASTE PROFILE CONSTRUCTOR    │
          └───────────────┬───────────────────┘
                          │
          ┌───────────────┼───────────────────┐
          ▼               ▼                   ▼
  ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐
  │   PHONETIC   │ │  TERRITORY & │ │  STYLE SCORING  │
  │   SIGNAL     │ │  RATIONALE   │ │                 │
  │   EXTRACTOR  │ │  AGGREGATOR  │ │ Tag frequency   │
  │              │ │              │ │ count from      │
  │ Liked names: │ │ Liked terri- │ │ liked reactions │
  │ • onset      │ │ tories:      │ │                 │
  │ • nucleus    │ │ • nature     │ │ Style scores:   │
  │ • coda       │ │ • vintage    │ │ classic: 0.72   │
  │ • syllables  │ │ • cultural   │ │ modern: 0.18    │
  │              │ │              │ │ nature: 0.54    │
  │ Disliked:    │ │ Rejected     │ │ ...             │
  │ • patterns   │ │ territories: │ │                 │
  │   to avoid   │ │ • lanes to   │ └────────┬────────┘
  └──────┬───────┘ │   exclude    │          │
         │         └──────┬───────┘          │
         └────────────────┼──────────────────┘
                          │
                          ▼
          ┌───────────────────────────────────┐
          │         TASTE PROFILE             │
          │                                   │
          │  liked_phonetics: [patterns]       │
          │  disliked_phonetics: [patterns]    │
          │  liked_territories: [tags]         │
          │  rejected_lanes: [tags]            │
          │  style_scores: {tag: score}        │
          │  liked_examples: [name list]       │
          │  rejected_examples: [name list]    │
          └───────────────────────────────────┘
                          │
              ┌───────────┴──────────┐
              ▼                      ▼
    ┌──────────────────┐   ┌──────────────────────┐
    │  Brief           │   │  Taste State         │
    │  Constructor     │   │  (advanced embodiment│
    │  (prompt enrich) │   │  — see Figure 9)     │
    └──────────────────┘   └──────────────────────┘
```

## Notes for Patent Illustrator
- Show the three parallel extractors feeding into the single TasteProfile object
- TasteProfile box should clearly list all fields
- Show the two downstream consumers: Brief Constructor and Taste State
- Formal figure should use standard flowchart/block diagram conventions (37 C.F.R. § 1.84)
