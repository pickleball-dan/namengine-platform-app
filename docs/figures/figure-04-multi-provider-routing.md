# Figure 4 — Multi-Provider Routing Flow

**Patent:** NamEngine Provisional Patent Application
**Figure:** 4 of 9
**Status:** Text specification — formal drawing required for non-provisional

## Description

Multi-provider routing flow: parallel or sequential provider dispatch, provider result collection, quality adapter scoring per candidate, candidate selection by score, fallback on shortfall.

## Text Diagram

```
           [NamingBrief + CNI]
                   │
                   ▼
    ┌──────────────────────────────┐
    │     GENERATION ROUTER        │
    │  (dispatch strategy:         │
    │   parallel or sequential)    │
    └──────┬───────────┬───────────┘
           │           │
           ▼           ▼
    ┌────────────┐  ┌────────────┐  (+ additional providers)
    │ Provider A │  │ Provider B │
    │ (e.g. GPT) │  │ (e.g.Claude│
    └──────┬─────┘  └─────┬──────┘
           │              │
           ▼              ▼
    ┌────────────────────────────┐
    │   RESULT COLLECTION        │
    │   Combine all candidates   │
    │   from all providers       │
    └──────────────┬─────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │   QUALITY ADAPTER SCORING    │
    │   Score each candidate on    │
    │   vertical-specific dims     │
    │   weighted by priority_      │
    │   weights + taste profile    │
    └──────────────┬───────────────┘
                   │
          ┌────────▼────────┐
          │ Sufficient high-│
          │ quality results?│
          └──┬──────────┬───┘
             │ Yes      │ No
             ▼          ▼
    ┌──────────────┐  ┌──────────────────────────┐
    │ Return top-N │  │ FALLBACK                  │
    │ candidates   │  │ • Retry with adjusted     │
    │ to user      │  │   prompt                  │
    └──────────────┘  │ • Add provider            │
                      │ • Relax quality threshold │
                      │ • Return best available   │
                      └──────────────────────────┘
```

## Notes for Patent Illustrator
- Show parallel provider dispatch clearly (two simultaneous arrows down)
- Fallback path is important — show as a distinct branch
- Quality adapter scoring is a separate distinct step after collection
- Formal figure should use standard flowchart conventions (37 C.F.R. § 1.84)
