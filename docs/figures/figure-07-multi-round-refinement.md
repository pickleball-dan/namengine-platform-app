# Figure 7 — Multi-Round Refinement Journey

**Patent:** NamEngine Provisional Patent Application
**Figure:** 7 of 9
**Status:** Text specification — formal drawing required for non-provisional

## Description

Multi-round refinement journey: Round 1 (broad set, e.g. 8 names), reaction capture, taste profile build, Round 2 (refined set using taste profile), Round 3 (finalist shortlist), compare/choose flow.

## Text Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  ROUND 1 — Broad Exploration                                    │
│                                                                 │
│  CNI (from intake) ──► Brief ──► Generation ──► 8 Candidates   │
│                                                      │          │
│                                            User Reacts to each  │
│                                                      │          │
│                                         Taste Profile Built     │
└──────────────────────────────────────────────┬──────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  ROUND 2 — Refined Set                                          │
│                                                                 │
│  CNI + TasteProfile ──► Enriched Brief ──► Generation          │
│  (Round 1 names excluded)                        │             │
│                                          8 Refined Candidates   │
│                                                  │             │
│                                        User Reacts to each      │
│                                                  │             │
│                                   TasteProfile Updated          │
└──────────────────────────────────────────────────┬──────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  ROUND 3 — Finalist Shortlist                                   │
│                                                                 │
│  CNI + TasteProfile ──► Highly Targeted Brief ──► Generation   │
│  (Rounds 1+2 names excluded)                          │        │
│                                              5–6 Finalists      │
│                                                       │        │
│                                             User Reacts         │
└───────────────────────────────────────────────────────┬─────────┘
                                                        │
                                                        ▼
                              ┌──────────────────────────────────┐
                              │  COMPARE & CHOOSE FLOW           │
                              │                                  │
                              │  All loved names (❤) from        │
                              │  Rounds 1 + 2 + 3 aggregated     │
                              │  Presented side-by-side          │
                              │  User selects final name         │
                              │  Stored as session result        │
                              └──────────────────────────────────┘
```

## Notes for Patent Illustrator
- Three round boxes stacked vertically, connected by arrows
- Each round box shows: input, generation, candidate count, reaction capture, profile update
- Compare & Choose is a distinct fourth stage below the rounds
- Emphasize that all prior names are excluded in each subsequent round
- Formal figure should use standard flowchart conventions (37 C.F.R. § 1.84)
