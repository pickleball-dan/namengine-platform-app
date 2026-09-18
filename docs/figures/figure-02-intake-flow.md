# Figure 2 — Sequential Intake Flow

**Patent:** NamEngine Provisional Patent Application
**Figure:** 2 of 9
**Status:** Text specification — formal drawing required for non-provisional

## Description

Sequential intake flow: one-question-at-a-time presentation, optional and required question handling, direction review screen, edit-from-review navigation, and confirmation before generation.

## Text Diagram

```
         [User Begins Intake]
                 │
                 ▼
    ┌────────────────────────┐
    │  Present Question N    │
    │  (one at a time)       │
    │  • Required or Optional│
    └────────────┬───────────┘
                 │
         ┌───────▼────────┐
         │ User Responds? │
         └───┬────────┬───┘
             │ Yes    │ No (optional only)
             ▼        ▼
    ┌──────────────┐  ┌──────────────────┐
    │ Record Answer│  │ Skip (no answer  │
    │ to Direction │  │ recorded)        │
    │ Profile      │  └────────┬─────────┘
    └──────┬───────┘           │
           └─────────┬─────────┘
                     │
              ┌──────▼──────┐
              │ More        │
              │ Questions?  │
              └──┬──────┬───┘
                 │ Yes  │ No
                 │      ▼
                 │  ┌───────────────────────┐
                 │  │ DIRECTION REVIEW       │
                 │  │ Show all answers       │
                 │  │ User may edit any      │
                 │  │ Edit → return to Q     │
                 │  │ then back to review    │
                 │  └──────────┬────────────┘
                 │             │ Confirmed
                 │             ▼
                 │  ┌───────────────────────┐
                 │  │ CNI Mapper            │
                 │  │ Normalize to CNI      │
                 │  │ object with           │
                 │  │ priority_weights      │
                 │  └───────────┬───────────┘
                 │              │
                 ◄──────────────┘ (loop back for next question)
```

## Notes for Patent Illustrator
- Vertical flowchart, top-to-bottom
- Key branch: optional question skip path
- Direction Review is a distinct screen/state — show as a separate box
- Edit-from-review loop should be clearly indicated with return arrow
- Formal figure should use standard flowchart conventions (37 C.F.R. § 1.84)
