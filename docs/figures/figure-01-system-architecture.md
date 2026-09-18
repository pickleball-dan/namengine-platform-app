# Figure 1 — System Architecture Overview

**Patent:** NamEngine Provisional Patent Application
**Figure:** 1 of 9
**Status:** Text specification — formal drawing required for non-provisional

## Description

System architecture overview showing the intake pipeline, canonical intent layer, model router, quality framework, storage layer, and refinement orchestrator.

## Text Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NAMENGINE PLATFORM                           │
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  INTAKE PIPELINE│    │  CANONICAL INTENT│    │  GENERATION     │  │
│  │                 │    │  LAYER           │    │  LAYER          │  │
│  │ • Question      │───►│ • CNI Mapper     │───►│ • Brief         │  │
│  │   Sequencer     │    │ • Priority       │    │   Constructor   │  │
│  │ • Direction     │    │   Weights        │    │ • Multi-Provider│  │
│  │   Review        │    │ • Schema         │    │   Router        │  │
│  │ • Confirmation  │    │   Versioning     │    │ • Quality       │  │
│  └─────────────────┘    └─────────────────┘    │   Adapter       │  │
│                                                 └────────┬────────┘  │
│                                                          │           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────▼────────┐  │
│  │  REFINEMENT     │    │  TASTE LAYER    │    │  REACTION       │  │
│  │  ORCHESTRATOR   │◄───│                 │◄───│  CAPTURE        │  │
│  │                 │    │ • Taste Profile  │    │                 │  │
│  │ • Session Chain │    │   Constructor   │    │ • Like / Dislike│  │
│  │ • Round Manager │    │ • Taste State   │    │ • Strong React  │  │
│  │ • Name Exclusion│    │ • Exploration   │    │ • Signal Extract│  │
│  │                 │    │   Planner       │    │                 │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     STORAGE LAYER                           │    │
│  │  Session Records · CNI Objects · Reaction Log · Taste State │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Notes for Patent Illustrator
- Top row: three boxes left-to-right (Intake → CNI → Generation)
- Bottom row: three boxes right-to-left (Reaction → Taste → Refinement)
- Storage layer spans full width at bottom
- Arrows show data flow direction
- Formal figure should use standard flowchart/block diagram conventions (37 C.F.R. § 1.84)
