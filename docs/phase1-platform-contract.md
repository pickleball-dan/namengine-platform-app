# Phase 1 Platform Contract

Phase 1 turns the NamEngine platform idea into a concrete shared contract. The
goal is not to redesign the product yet. The goal is to stop each vertical from
owning separate versions of the same naming concepts.

## Contract Objects

- `VerticalConfig`: what a vertical is, what it asks, how it frames prompts, and
  which validation modules it wants.
- `NamingBrief`: the normalized user brief after intake.
- `NameResult`: the common card payload every vertical can render.
- `Reaction`: the shared `Love / Maybe / No` feedback event.
- `TasteProfile`: the session-level taste signal inferred from reactions.
- `RefinementRequest`: a request for the next batch based on the brief and taste.
- `ValidationResult`: structured validation metadata for each result.
- `NamingSession`: the parent object tying brief, results, reactions, and taste
  together.
- `ChosenName`: the commitment moment after a user chooses a name.

## First Migration Target

Pet should move first because it tests the shared engine without Business domain
complexity or Baby's higher emotional stakes.

The first end-to-end milestone is:

1. Load the `pet` vertical config.
2. Normalize intake into `NamingBrief`.
3. Generate `NameResult` objects.
4. Store a `NamingSession`.
5. Capture `Reaction` events.
6. Update a `TasteProfile`.
7. Produce a refined batch from `RefinementRequest`.
8. Create a `ChosenName` and share page.

