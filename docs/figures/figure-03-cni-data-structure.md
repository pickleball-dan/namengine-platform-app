# Figure 3 — Canonical Naming Intent (CNI) Data Structure

**Patent:** NamEngine Provisional Patent Application
**Figure:** 3 of 9
**Status:** Text specification — formal drawing required for non-provisional

## Description

Canonical Naming Intent data structure showing fields: vertical, naming_target, gender_context, cultural_contexts, naming_styles, familiarity_preference, distinctiveness_preference, sound_qualities, emotional_qualities, priority_weights, and extensions.

## Text Diagram

```
┌──────────────────────────────────────────────────────────────┐
│               CANONICAL NAMING INTENT (CNI)                  │
│                    intent_version: 2                         │
├─────────────────────────┬────────────────────────────────────┤
│ DOMAIN FIELDS           │ EXAMPLE VALUE                      │
├─────────────────────────┼────────────────────────────────────┤
│ vertical                │ "baby"                             │
│ naming_target           │ "girl"                             │
│ gender_context          │ "feminine"                         │
│ cultural_contexts       │ ["irish", "french"]                │
├─────────────────────────┼────────────────────────────────────┤
│ STYLE FIELDS            │                                    │
├─────────────────────────┼────────────────────────────────────┤
│ naming_styles           │ ["classic", "elegant"]             │
│ familiarity_preference  │ "moderately_familiar"              │
│ distinctiveness_pref.   │ "somewhat_distinctive"             │
│ sound_qualities         │ ["soft", "melodic"]                │
│ emotional_qualities     │ ["warm", "strong"]                 │
├─────────────────────────┼────────────────────────────────────┤
│ PRIORITY WEIGHTS ★      │                                    │
├─────────────────────────┼────────────────────────────────────┤
│ priority_weights        │ {                                  │
│                         │   "style": 0.6,                   │
│                         │   "phonetics": 0.3,               │
│                         │   "distinctiveness": 0.1          │
│                         │ }                                  │
├─────────────────────────┼────────────────────────────────────┤
│ SCHEMA FIELDS           │                                    │
├─────────────────────────┼────────────────────────────────────┤
│ intent_version          │ 2                                  │
│ extensions              │ { vertical-specific fields }       │
└─────────────────────────┴────────────────────────────────────┘

★ priority_weights propagate into:
   ┌──────────────────────────────┐
   │  Quality Adapter Scoring     │ ← dimension weights adjusted
   │  Taste Thesis Builder        │ ← prompt emphasis adjusted
   │  Exploration Planner         │ ← exploration targets weighted
   └──────────────────────────────┘
```

## Notes for Patent Illustrator
- Present as a structured data table / entity diagram
- Highlight priority_weights row distinctively (it is the key novel field)
- Show the three downstream consumers of priority_weights as a separate callout box
- Formal figure should use standard block/table diagram conventions (37 C.F.R. § 1.84)
