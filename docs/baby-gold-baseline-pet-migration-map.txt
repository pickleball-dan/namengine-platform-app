# Baby Gold Baseline + Pet Migration Map

_Last updated: 2026-07-23_

## Purpose

Baby is now treated as the protected gold-standard implementation of the new NamEngine intelligence platform.

The next migration target is Pet. Pet should inherit the proven shared intelligence-platform behavior from Baby without mutating, weakening, or visually replacing Baby.

This document is the living working map for that migration. It should be updated as we inspect, migrate, test, and verify.

## Current Gold Baseline Snapshot

| Item | Current value |
| --- | --- |
| Gold-standard vertical | Baby |
| Migration target | Pet |
| Baseline branch at doc creation | `feature/baby-progress-overlay-current-main` |
| Baseline commit at doc creation | `183ac55` |
| Proposed baseline tag | `baby-gold-standard-v1` |
| Snapshot date | 2026-07-23 |
| Test status | Baby-focused baseline gate passed: `110 passed in 7.71s` on 2026-07-23 |
| Screenshot status | Fresh mobile baseline screenshots captured on 2026-07-23 under `docs/baselines/baby-gold-standard-v1/screenshots/`; visual pass found no obvious broken assets or horizontal overflow, with human review still recommended before tagging |
| Working tree note | Baseline docs, `.txt` copy, small baseline fix, and official baseline screenshot artifacts are currently uncommitted/untracked and should be reviewed before tagging. Old local `test-results/` artifacts remain untracked and should not be included in the gold tag unless intentionally moved. |

## Ground Rules

1. **Baby is protected.**
   - Do not change Baby copy, layout, theme, assets, intake behavior, results behavior, or refinement behavior while migrating Pet unless the change is explicitly part of a shared-engine fix and Baby regression is reverified.

2. **Pet gets its own migration branch.**
   - Pet migration work should not happen directly on the Baby baseline branch.
   - Recommended next branch name: `feature/pet-intelligence-platform-migration`.

3. **Shared engine changes require Baby regression.**
   - Any change to shared routing, persistence, AI orchestration, progress events, scoring, results composition, reaction handling, refinement, compare, share, or chosen-card behavior must trigger a Baby regression check.

4. **Pet must preserve Pet.**
   - The goal is not to make Pet look or sound like Baby.
   - Pet should inherit the intelligence platform structure while preserving Pet’s own audience, emotional tone, graphics, colors, question language, result-card language, and naming personality.

5. **No deploy/push until local gate is green.**
   - Follow the local-first NamEngine release train: batch related changes, run the local gate, inspect screenshots, then push/deploy only when green.

6. **No Maybe in customer-facing UI.**
   - Baby and Pet customer-facing result/detail/reaction surfaces must not expose a Maybe reaction, `data-reaction-value="maybe"`, or "Keep as a maybe" copy.
   - Legacy/internal backend, storage, audit, and taste-evolution handling may continue to understand historical `maybe` rows until intentionally migrated.

## Baby Acceptance Checklist

Before Baby is tagged as the gold standard, verify and record the following.

### 1. Intake Flow

- [ ] Baby entry route loads cleanly on mobile.
- [ ] Intake questions render in the intended order.
- [ ] Required questions block advancement until answered.
- [ ] Optional questions allow skipping without awkward copy or duplicate controls.
- [ ] Grouped intake structure is clear and emotionally appropriate.
- [ ] No internal/plumbing labels leak into the user-facing UI.
- [ ] Copy helps the user make decisions rather than merely filling space.

### 2. Progress / Intelligence Overlay

- [ ] Progress overlay appears at the right time.
- [ ] Progress language explains the intelligence work in user-facing terms.
- [ ] Overlay does not feel stalled, fake, or overly technical.
- [ ] Completion transitions naturally into results.
- [ ] Mobile spacing and readability are acceptable.

### 3. Results

- [ ] Name cards render correctly.
- [ ] Explanations are specific, useful, and emotionally appropriate for Baby.
- [ ] Results feel curated rather than generic.
- [ ] No duplicate or contradictory reasoning appears.
- [ ] Ranking/scoring language is clear but not overly mechanical.

### 4. Reactions + Refinement

- [ ] Reaction controls are clear.
- [ ] The 3-reaction refinement gate behaves correctly.
- [ ] Reaction state persists as expected.
- [ ] Refinement request uses prior reactions meaningfully.
- [ ] Round 2+ results preserve continuity without feeling repetitive.

### 5. Compare / Share / Chosen Card

- [ ] Compare flow works and helps decision-making.
- [ ] Share links work after refresh/reopen.
- [ ] Chosen-card route persists correctly.
- [ ] Chosen-card image generation is non-blocking.
- [ ] Baby chosen-card visual direction remains Baby-specific, not generic.

### 6. Mobile QA

- [x] Primary Baby path captured in mobile screenshots.
- [x] Intake, progress, results, compare, and chosen-card views checked on mobile width.
- [x] No obvious horizontal overflow or broken assets found in automated/mobile visual inspection; results/compare/share full-page captures are very tall and should receive human review before final tag.
- [x] Pet migration does not begin until baseline screenshots are available or intentionally deferred with a note.

### 7. Test Gate

Record fresh test command and result here before tagging.

```text
2026-07-23 Baby-focused baseline gate:
python -m pytest tests/test_baby_checkin_v1.py tests/test_baby_conversational_intake_v1.py tests/test_baby_decision_support.py tests/test_baby_flow_polish_v1.py tests/test_baby_intelligence_v1.py tests/test_baby_refinement_generation_cache.py tests/test_baby_taxonomy_ai_generation_v1.py tests/test_baby_taxonomy_v1.py tests/test_baby_ui_consistency.py tests/test_phase19_baby_smoke_validation.py tests/test_phase20_feelings_scale.py tests/test_phase27_baby_cultural_heritage_dropdown.py tests/test_phase28_baby_name_fact_card.py tests/test_phase29_baby_african_heritage_lane.py tests/test_phase30_baby_popularity_snapshot.py tests/test_phase31_baby_japanese_girl_heritage_lane.py tests/test_phase32_baby_ai_primary_generation.py tests/test_phase33_ai_primary_route_failsafe.py tests/test_phase34_baby_llm_prompt_quality_contract.py tests/test_phase37_baby_session_stale_fallback_block.py tests/test_phase38_generation_unavailable_copy.py

Result: 110 passed in 7.71s.

Baseline note: initial run found 2 feelings-scale failures. Fixed stale Baby final-step copy expectation and changed social `og:url` to use `request.base_url` so hidden feelings-scale query params do not leak into social metadata.
```

## Migration Map

| Baby behavior to preserve | Shared engine / platform piece | Baby-specific piece | Pet equivalent | Risk to Baby | Migration approach |
| --- | --- | --- | --- | --- | --- |
| Guided intake with grouped questions | Intake schema/rendering pattern, route flow, validation/skip behavior | Baby question copy, parent-focused emotional framing, baby visual treatment | Pet-owner intake with pet-specific question language and emotional cues | Medium | Extract/reuse structure only; keep vertical copy/theme isolated. |
| Progress overlay during generation | Progress event model, status endpoint/stream/polling, loading-to-results transition | Baby-specific progress phrases and emotional reassurance | Pet-specific progress language about personality, fit, and name feel | High | Reuse progress plumbing; configure vertical text separately. Baby regression required if plumbing changes. |
| Curated results cards | Result composition, card rendering pattern, scoring/explanation shape | Baby naming rationale, family/meaning/tone language | Pet name rationale around personality, sound, friendliness, memorability | Medium | Map shared data contract first, then preserve Pet copy/visual style. |
| Reaction controls | Reaction persistence, reaction event handling, refinement input | Baby reaction labels/tone if verticalized | Pet reaction labels/tone if verticalized | High | Reuse persistence and refinement signals; do not alter Baby reaction semantics without tests. |
| 3-reaction refinement gate | Threshold logic, refinement trigger, Round 2+ orchestration | Baby guidance copy around refining names | Pet refinement guidance around narrowing pet-name vibe | High | Confirm gate is shared and configurable; run Baby regression after migration. |
| Round 2+ refined results | AI orchestration, prior-result context, reaction-informed prompt strategy | Baby prompt framing and constraints | Pet prompt framing and constraints | High | Separate prompt templates/config by vertical before changing Pet. |
| Compare flow | Compare route/data model/card selection behavior | Baby compare copy and card styling | Pet compare copy and card styling | Medium | Reuse compare mechanics; validate Baby compare unchanged. |
| Share links | Persistent result/session identifiers, share route behavior | Baby share copy/metadata | Pet share copy/metadata | High | Avoid shared persistence changes unless covered by tests. |
| Chosen-card persistence | Chosen route, saved selection, stable storage | Baby keepsake/blanket visual direction | Pet keepsake/card visual direction likely pet-themed | High | Verify persistent storage contract before adapting Pet. |
| Non-blocking chosen-card image generation | Async/background image-generation trigger and fallback display | Baby-specific image prompt/style | Pet-specific image prompt/style | Medium | Keep image generation vertical-configured; ensure Baby route does not wait on image completion. |
| Mobile-first polish | Shared responsive shell/card spacing conventions | Baby color palette, graphics, typography accents | Pet palette, graphics, typography accents | Low/Medium | Use shared CSS variables/asset slots where possible; avoid global CSS drift. |

## Pet Migration Phases

### Phase 0 — Freeze Baby Baseline

- [x] Review working tree and decide what to do with untracked `test-results/`; official baseline screenshots moved to `docs/baselines/baby-gold-standard-v1/screenshots/`, leaving old temporary test artifacts untracked.
- [x] Run Baby-focused test gate.
- [x] Capture Baby mobile screenshots.
- [x] Create baseline tag: `baby-gold-standard-v1`.
- [ ] Create Pet migration branch from the approved baseline.

### Phase 1 — Inventory Pet vs Baby

- [ ] Identify current Pet routes, templates, static assets, prompts/config, tests, and persistence paths.
- [ ] Compare Pet’s current behavior against Baby’s gold-standard behavior.
- [ ] Mark Pet items as: already compatible, needs shared-engine migration, Pet-specific preserve, or obsolete.

### Phase 2 — Shared Engine Adaptation

- [ ] Map Baby shared engine pieces to Pet.
- [ ] Keep vertical-specific config separate.
- [ ] Avoid Baby edits unless a shared bug is discovered.
- [ ] Add/adjust tests around shared behavior before broad UI changes.

### Phase 3 — Pet UI/UX Preservation

- [ ] Restore or preserve Pet visual identity.
- [ ] Preserve Pet emotional tone and naming logic.
- [ ] Confirm mobile-first layout.
- [ ] Verify no Baby-specific language appears in Pet.

### Phase 4 — Regression + Screenshots

- [ ] Run Baby regression gate.
- [ ] Run Pet migration gate.
- [ ] Capture Baby screenshots after shared changes.
- [ ] Capture Pet screenshots after migration.
- [ ] Inspect content quality, not just route loading.

### Phase 5 — Release Decision

- [ ] Review diff for accidental Baby changes.
- [ ] Review screenshots side-by-side.
- [ ] Confirm local gate is green.
- [ ] Push/deploy only after the migration branch is stable.

## Open Questions / Decisions

- [x] Should `baby-gold-standard-v1` be an annotated git tag or only a branch marker? Decision: annotated git tag.
- [ ] Which exact Baby test command defines the baseline gate?
- [x] Which screenshots are required for the baseline package? Current package: mobile intake, cultural-context intake, final priority/feelings, progress overlay, results, compare, share, and chosen card.
- [ ] Should Pet migration start from current Baby branch or after merging Baby baseline into main?
- [ ] Which Pet legacy files/assets are the product reference for visual and emotional preservation?

## Change Log

| Date | Change |
| --- | --- |
| 2026-07-23 | Prepared baseline package for annotated git tag `baby-gold-standard-v1`. |
| 2026-07-23 | Added gold-standard rule: Maybe must not appear in Baby/Pet customer-facing UI, while legacy/internal maybe handling may remain for historical data. |
| 2026-07-23 | Moved official Baby baseline screenshots into `docs/baselines/baby-gold-standard-v1/screenshots/` so the gold tag includes a visual contract, while leaving old temporary `test-results/` artifacts untracked. |
| 2026-07-23 | Captured Baby mobile baseline screenshots for intake, cultural-context intake, final priority/feelings, progress overlay, results, compare, share, and chosen card. |
| 2026-07-23 | Baby-focused baseline gate passed: `110 passed in 7.71s`; documented small baseline fix for feelings-scale/social-meta cleanliness. |
| 2026-07-23 | Created initial living working document for Baby gold baseline and Pet migration planning. |
