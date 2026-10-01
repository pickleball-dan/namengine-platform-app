# SOE Vertical Contract

SOE means Standardization of Engine. NamEngine should operate as one shared naming engine with many vertical identities.

The rule: the engine, route lifecycle, telemetry, and release checks are shared. The visuals, copy voice, graphical artifacts, and domain-specific judgment stay vertical-specific.

## Core Implementation Rules

A vertical may extend the shared engine, but it should not bypass it.

Vertical-specific behavior should live in adapters, validators, configuration, prompts, visual components, or artifact handlers that are called by the shared lifecycle. If Pet needs special validation, that should be a Pet adapter called by the shared lifecycle, not an `if vertical == "pet"` branch buried inside a route. The same rule applies to Business, Boat, Baby, and every future vertical.

Slug checks are considered migration debt unless they are strictly presentation-layer concerns.

A slug check deciding which logo, visual treatment, or presentation-only copy to show may be acceptable. A slug check deciding generation flow, session persistence, telemetry, paywall behavior, result handling, review behavior, or saved/share behavior is a candidate for SOE migration.

## Why This Exists

NamEngine has active verticals that work, but some behaviors still live in slug-specific branches. That makes every new vertical more expensive than it should be and creates the kind of patchwork that led to Pet fixes landing in several different places.

This contract is the implementation map for moving toward:

- one intake lifecycle
- one review lifecycle
- one generation lifecycle
- one Mission Control reporting lifecycle
- one results/save/share/paywall lifecycle
- one graphical artifact lifecycle
- vertical-specific identity through configuration and adapters

## Active Vertical Scope

Active public verticals:

- Baby
- Pet
- Business
- Boat

Future or incomplete verticals:

- Product
- Character

Future verticals should not be included in release blockers until they are explicitly marked active and have complete required assets, QA fixtures, and graphical artifact decisions.

## Shared Lifecycle

Every active vertical should fit this lifecycle, even if one step is configured off.

1. Landing or vertical entry
2. Intake
3. Optional direction review
4. Progress/generation experience
5. Results
6. Reaction capture
7. Save/share
8. Paywall or access gate where appropriate
9. Detail page
10. Chosen artifact
11. Mission Control reporting

The goal is not identical screens. The goal is identical contracts.

## Vertical Configuration Contract

Each vertical should declare the following through configuration or an adapter, not ad hoc route checks:

| Area | Required decision |
| --- | --- |
| Active status | active, staging-only, or future |
| Intake mode | grouped form, guided one-question flow, or other approved mode |
| Review mode | direct-to-generation or direction-review page |
| Result count | default first-list count and later-round counts |
| AI policy | AI-primary, fallback-allowed, or fallback-only |
| Generation QA | at least one fast fixture for active verticals |
| Mission Control | provider/model/cost/session reporting required |
| URL privacy | no long personal intake strings after review/results handoff |
| Save/share | supported, disabled, or staged |
| Paywall | free first list, locked refinement, chosen gate, or other policy |
| Graphical artifacts | generation graphic, result identity graphic, chosen artifact, share image |

If this information lives in templates or route conditionals today, SOE work should move it toward configuration over time.

## Intake Contract

Every vertical intake must:

- render from `VerticalConfig.intake_questions`
- preserve native form controls so server submission is reliable
- support required and optional questions
- support single-select and multi-select choices through `Question.max_select`
- preserve user inputs when editing from review or results
- keep long or personal values out of durable visible URLs where practical
- avoid visible Skip actions unless explicitly approved
- use vertical-specific voice without changing field names casually

Shared section structure should be preferred:

- About the subject
- Name style
- Fit and feeling

A vertical may use a different grouping only when the naming task needs it.

## Review Contract

The direction review should be a configured capability, not a hard-coded Pet/Business special case.

When enabled, review must:

- show all intake answers, including blank optional fields
- provide edit links back to the source question
- submit preserved answers as form data, not only as action-query strings
- invoke the same progress overlay as direct generation
- avoid long personal query strings in the browser URL after submit

When disabled, the vertical may go directly from intake to generation, but results must still preserve direction data.

## Generation Contract

Every active vertical must use the shared `generate_names()` entrypoint.

Vertical-specific behavior belongs in:

- AI prompt context
- taste strategy inputs
- candidate/finalizer expectations
- quality adapter
- validation modules
- fallback generator if fallback output is user-visible

An active AI-primary vertical must prove two things:

- fallback structural behavior does not crash
- live AI generation reports correctly to Mission Control

Fallback structural QA is not a substitute for live AI quality review.

## Mission Control Contract

Every generation that reaches the user should be classifiable as one of:

- live AI generation
- fallback generation
- cached session served
- failed generation

Mission Control should show enough information to distinguish those cases.

Minimum reporting fields:

- session ID
- generation ID or run ID when available
- vertical
- round number
- provider
- model
- prompt version
- request stages
- latency
- token usage
- estimated cost
- result count
- fallback or cache status
- created/updated timestamp that reflects the generation event

If a row cannot appear in Mission Control, that is a release risk.

## Results Contract

Every active vertical result page must preserve:

- vertical identity
- result cards
- direction summary
- validation/trust cue
- reactions
- detail links
- choose action
- save/share where supported
- paywall behavior where required
- refinement/new-list controls where allowed

The result cards may differ by vertical, but their data contract should stay stable.

## Graphical Artifact Contract

Every active vertical needs decisions for these visual slots:

| Slot | Purpose | Examples |
| --- | --- | --- |
| Generation graphic | What the user sees while names are created | pet paw/portrait motion, baby keepsake motion, boat nautical motion |
| Result identity graphic | The visual language around result cards and detail pages | logo, motif, validation badges |
| Chosen artifact | The celebratory/premium artifact after choosing | pet portrait, baby embroidered name, business brand card, boat transom/nameplate |
| Share image | Social preview and saved-list preview | vertical Open Graph image |

Each slot should be either implemented, intentionally disabled, or explicitly staged. No active vertical should have an accidental missing graphic.

## QA Contract

An active vertical is SOE-ready only when all of these pass:

- intake route renders
- intake can submit with realistic answers
- review behavior matches the vertical configuration
- progress graphic appears during generation
- results show a non-empty direction summary
- results show the expected number of names
- Mission Control records the run or explicitly marks fallback/cache status
- save/share works or is intentionally disabled
- paywall gates the intended actions
- detail page opens
- chosen artifact works or is intentionally disabled
- Generation QA has at least one fixture
- live AI-primary verticals have an explicit AI-mode verification

## Staging Rule

SOE work should happen on staging first when it touches shared lifecycle behavior or more than one vertical.

Use production only for:

- focused one-vertical fixes
- urgent regressions
- deploys that already passed staging verification

## Migration Order

Recommended order:

1. Define active/future vertical status in code.
2. Move review behavior into vertical configuration.
3. Move URL privacy rules into shared helpers.
4. Standardize progress/generation form behavior.
5. Standardize Mission Control generation event reporting.
6. Standardize graphical artifact slots.
7. Add or update QA fixtures for every active vertical.
8. Retire stale slug-specific branches only after tests prove parity.

## Non-Goals

SOE is not a redesign. It should not flatten vertical identities or make every vertical look the same.

SOE is also not a rewrite. Migrate small pieces behind tests, one contract at a time.
