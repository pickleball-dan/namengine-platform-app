# NamEngine Platform App

This is the shared NamEngine platform being built beside the existing vertical
apps. Phase 1 defines the platform contract: shared schemas and vertical
configuration objects that Baby, Business, Pet, and Character can all use.
Phase 2 adds the thin Flask shell that renders intake from those configs.

The current vertical apps remain the reference implementation while this app is
built out.

## Phase 1 Contract

The shared contract lives in `namengine/core/schemas.py` and defines:

- `NamingBrief`
- `VerticalConfig`
- `TasteProfile`
- `NameResult`
- `Reaction`
- `RefinementRequest`
- `ValidationResult`
- `NamingSession`
- `ChosenName`

Vertical definitions live in `namengine/verticals/configs.py`.

## Phase 2 Web Shell

The Flask app lives in `app.py`.

Current routes:

- `/` lists the verticals from the shared registry.
- `/<vertical>` renders an intake form from that vertical's `VerticalConfig`.

Pet is the first migration target, so `/pet` is the route to use for the next
engine milestone.

## Phase 3 Pet Results

`/pet/results` now normalizes query-string intake into `NamingBrief`, generates
shared `NameResult` objects through `namengine/core/generation.py`, and renders
the shared results template.

The current generator is a deterministic fallback. It exists to prove the
platform contract and UI route before live model calls, persistence, reactions,
and refinement are added behind the same interface.

## Phase 4 Reaction Capture

`/api/react` validates reaction payloads and returns a shared `Reaction` object.
The results page sends `Love / Maybe / No` button clicks to that endpoint and
marks the selected state in the browser.

Phase 4 does not persist reactions. Persistence starts in Phase 5 with local
SQLite and a Postgres-ready storage boundary.

## Phase 5 SQLite Storage

Phase 5 adds local SQLite persistence in `namengine/core/storage.py`.

Persisted objects:

- sessions
- generated name results
- reactions

The local database defaults to `data/namengine.sqlite3`. Override with
`NAMENGINE_DB_PATH` for tests or alternate local runs.

## Phase 6 Chosen Name

Each result card now has `Choose this name`. Submitting it persists a
`ChosenName` row and redirects to `/chosen/<id>`, a shareable single-name page.

The session table also carries the first round metadata needed by later refine
cycles: `round_number`, `parent_session_id`, and `refinement_prompt`.

## Phase 7 Refinement Rounds

`/refine` creates child sessions from stored reactions:

- Round 1: discovery, 8 names
- Round 2: refined, 8 names
- Round 3: finalists, 5-6 names
- Round 4: optional one-more-round escape hatch

The current implementation still uses deterministic fallback pools, but the
storage and route contract are shaped for the future AI refinement engine.

## Phase 8 Compare Favorites

`/compare/<session_id>` gathers decision candidates from the session chain:

- loved names first
- maybe names if there are not enough loved names
- latest finalists as fallback

The page shows up to six names with decision-focused tradeoffs and a direct
`Choose this name` action.

## Phase 9 Taste Profile

Reactions now build a persisted `TasteProfile` that captures loved names,
maybe names, rejected names, sound signals, style preferences, rejected lanes,
and a short summary. Refinement and Compare can use that profile instead of
only raw reaction counts.

## Phase 10 Validation Pipeline

Validation now lives in `namengine/core/validation.py` and persists to a
separate `validation_results` table. Pet currently validates callability, sound
clarity, and avoid-list conflicts.

## Phase 11 AI Generation Layer

`namengine/core/ai_generation.py` adds the OpenAI-backed generation boundary:

- strict JSON prompt contract
- parser into shared `NameResult`
- duplicate-name filtering
- validation after AI output
- deterministic fallback when `OPENAI_API_KEY` is missing or a live call fails

Use `NAMENGINE_OPENAI_MODEL` to override the default model.

## Phase 12 Model Router + Quality Harness

`namengine/core/model_router.py` introduces provider orchestration:

- `ModelProvider`
- `ProviderResult`
- `GenerationCandidate`
- provider routing for OpenAI + fallback
- placeholder provider errors for Claude, Gemini, and Groq until their SDKs are wired
- candidate quality scoring and deduping

`namengine/core/quality.py` adds a repeatable harness for fixed briefs. The
first Pet fixtures live in `tests/fixtures/pet_quality_briefs.json`.

## Phase 13 Provider Performance Learning

`namengine/core/provider_performance.py` summarizes persisted behavior by model
provider. The storage layer refreshes provider performance after reactions and
chosen-name events, tracking generated count, reaction mix, love rate, choose
rate, average quality score, and an overall performance score.

## Phase 14 Progress Experience

Generation and refinement forms now show a short progress experience while the
request is running. The copy describes useful work, not backend plumbing:
reading the brief, checking fit and callability, comparing naming strategies,
and selecting the strongest names. Results also show a small trust cue such as
`Selected from 8 candidates and filtered for fit, callability, distinctiveness.`

## Phase 15 Pet Product QA

Pet has been walked end to end on mobile and desktop:

- intake
- progress
- results
- reactions
- refinement
- finalists
- compare
- choose

The QA pass tightened Compare so it fills to six decision candidates from the
latest finalists, and condensed mobile validation signals so result cards stay
scannable. Notes live in `docs/phase15-pet-product-qa.md`.

## Phase 16 Vertical UI Contract

Each vertical now carries the UI-facing pieces needed to reuse the platform
without template drift:

- theme colors
- logo asset
- share image asset
- result labels
- intake questions
- validation modules

`namengine/core/vertical_ui.py` validates the required theme and asset keys.
The shared templates consume those values, so Baby, Business, Character, and
future verticals can inherit the same flow while still feeling distinct.

## Phase 17 Baby Vertical Migration

Baby now uses the same structural flow as Pet:

- grouped intake
- progress overlay
- results
- Love / Maybe / No reactions
- 3-reaction refinement gate
- Round 2+ refinement
- compare favorites
- share list
- chosen-name page
- persisted sessions, reactions, taste profile, and chosen names
- non-blocking chosen-name image preparation

Baby has its own intake fields, soft nursery palette, logo/share assets,
fallback name pools, validation modules, and chosen-name keepsake treatment.
The selected-name image prompt uses a baby blanket with the chosen name
embroidered on it, not a baby photo.

## Phase 18 Business Vertical Launch

Business now uses the shared vertical system as a launch-ready founder/operator
workflow:

- grouped intake for business context, name style, and launch fit
- Business-specific palette, logo, and share image
- Business fallback name pools
- result labels for positioning, brand fit, and launch risks
- directional validation for domain signal, category fit, and launch risk
- GoDaddy domain quick-check panels when `GODADDY_API_KEY` and
  `GODADDY_API_SECRET` are configured
- taste history and refinement through the shared platform flow

Launch notes live in `docs/business-vertical-launch-2026-07-06.md`.

## Vertical Graphics Framework

Pet is the visual standard for new verticals. Use
`docs/vertical-graphics-template.md` before launching a new naming category,
then start from `docs/vertical-graphics-config-examples.yaml` to define the
vertical's tone, audience, palette, motif, hero direction, result-card treatment,
and supporting visual elements.

The framework keeps every vertical visually distinct while preserving the
NamEngine identity: calm, intelligent, warm, refined, simple, emotionally aware,
and discovery-focused.

The live implementation contract now also includes a typed `VerticalVisualConfig`
inside each `VerticalConfig`. See `docs/vertical-config-schema.md` for the field
shape and `docs/vertical-launch-checklist.md` for the launch checklist.

## Verify

```powershell
python -m unittest discover -s tests
```
