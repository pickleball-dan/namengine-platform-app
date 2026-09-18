# Figure 8 — Multi-Vertical Configuration Schema

**Patent:** NamEngine Provisional Patent Application
**Figure:** 8 of 9
**Status:** Text specification — formal drawing required for non-provisional

## Description

Multi-vertical configuration schema: slug, display_name, intake_questions, prompt_context, quality adapter registration, and vertical-specific visual configuration.

## Text Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│               VERTICAL REGISTRY                                 │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   BABY       │  │   PET        │  │  BUSINESS    │  + more  │
│  │   vertical   │  │   vertical   │  │  vertical    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                  │                  │
└─────────┼─────────────────┼──────────────────┼──────────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌──────────────────────────────────────────────────────────────────┐
│               VERTICAL CONFIGURATION OBJECT                      │
├──────────────────────────┬───────────────────────────────────────┤
│ FIELD                    │ PURPOSE                               │
├──────────────────────────┼───────────────────────────────────────┤
│ slug                     │ Unique identifier ("baby")            │
│ display_name             │ User-facing label ("Baby Names")      │
│ intake_questions         │ Ordered list of domain-specific Qs    │
│ prompt_context           │ Domain framing for AI generation      │
│ quality_adapter_class    │ Registered adapter for this vertical  │
│ score_dimensions         │ Vertical-specific scoring dims+weights│
│ assets.share_image       │ Social share image path               │
│ assets.logo              │ Vertical logo file                    │
│ visual.primary_color     │ Vertical accent color                 │
│ visual.font_family       │ Vertical-specific typography          │
└──────────────────────────┴───────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────┐
│               SHARED PLATFORM BEHAVIOR                           │
│  (identical across all verticals)                                │
│                                                                  │
│  • Intake sequencer    • CNI Mapper      • Generation Router     │
│  • Quality Adapter     • Reaction Capture • Session Chain       │
│  • Taste Profile       • Round Manager   • Compare/Choose       │
└──────────────────────────────────────────────────────────────────┘
```

## Notes for Patent Illustrator
- Top: three vertical boxes side by side (Baby, Pet, Business) feeding into shared config structure
- Middle: configuration schema as a two-column table
- Bottom: shared behavior box spanning full width — emphasize identical behavior across verticals
- This figure establishes the core architectural principle: functionality identical, presentation varies
- Formal figure should use standard block/table diagram conventions (37 C.F.R. § 1.84)
