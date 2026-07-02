# Legacy UI Migration Audit

Date: 2026-07-02

## Principle

The platform app is an engine consolidation, not a UI reset.

The older vertical apps are mature product references. They should be treated as the source of truth for interaction patterns, content hierarchy, visual assets, and decision-support flows. The new platform should keep the shared engine, storage, model-router, validation, reaction, refinement, compare, and chosen-name foundation, then migrate the prior UI structures into reusable platform components.

## Source Apps

- `namengine_pet_app`
- `baby_naming_app`
- `namengine_business_app`
- `namengine_character_app`
- `namengine_landing_page`

## Current Platform Strengths

- Shared vertical schema and intake contract.
- Shared Flask routes and templates.
- SQLite persistence with Render disk support.
- Reactions, taste profile updates, refinement, compare, and chosen-name persistence.
- AI generation boundary, fallback generation, quality checks, model routing, and provider performance learning.
- Deployed Render staging with verified Pet loop and durable chosen-name links.

These should stay as the base.

## Current Platform Gaps Against Legacy Apps

### Intake

Legacy Pet had a richer product entry experience:

- Hero plus path choice between standard names and original-name creation.
- Process disclosure that explained the naming flow without exposing technical plumbing.
- Brief-builder layout with a live brief panel.
- Taste history panel showing loved names from the visit.
- More developed form rhythm and helper copy.

Current platform Pet has the right grouped structure, but it does not yet fully restore the live brief, taste history, original-name lane, or the richer front-door composition.

### Results

Legacy Pet results had stronger decision support:

- Summary panel for the user's brief.
- Reaction effect note explaining what reactions do in human terms.
- Result cards with deeper hierarchy: name, pronunciation, why it fits, style/origin/meaning, fit preview, and detail link.
- Image-based reaction buttons using approved Love/Maybe/No assets.
- Saved reaction state and reaction feedback.
- Progress notes that made the round/refinement loop feel intentional.
- Share/shortlist affordances.

Current platform results cover the functional loop but are still thinner than the legacy results experience.

### Detail, Chosen, And Share

Legacy Pet had:

- Dedicated name detail pages.
- Rich chosen-name hero with celebration styling.
- Name essentials, why-it-fits, and chosen-from context.
- Native share plus copy fallback.
- Shared shortlist pages with social metadata.

Current platform chosen pages persist and share, but the detail/share layer needs more of the legacy structure.

### Original Name Mode

Legacy Pet had a separate original-name creation path:

- Original Pet Name Studio.
- Original brief form.
- Original results.
- Originality-focused copy and confidence notes.

Current platform does not yet restore that lane.

### Feedback

Legacy Pet included beta feedback capture and feedback response views.

Current platform does not yet restore this flow.

### Assets

Legacy verticals included approved assets:

- Vertical logos.
- Share images.
- Reaction images.
- Social preview assets.

Current platform has begun reusing visual assets, but this should continue systematically by vertical.

## Migration Strategy

Do not copy each old app wholesale into the platform. Instead, port the durable patterns into shared components.

### Phase 1: Pet Parity Components

Build shared component equivalents for:

- Hero/path-choice section.
- Brief-builder layout.
- Live brief summary.
- Taste history panel.
- Result summary panel.
- Result card with fit preview.
- Reaction image controls.
- Reaction feedback and saved state.
- Progress/refinement note.
- Share actions with native share and copy fallback.
- Chosen context panel.

Apply them to Pet first.

### Phase 2: Pet Missing Flows

Restore:

- Original-name creation lane.
- Name detail page.
- Shared shortlist page.
- Feedback page.

Keep these wired to the new platform storage and route architecture instead of reintroducing one-off storage.

### Phase 3: Vertical Migration

Use the same shared components for:

- Baby naming.
- Business naming.
- Character naming.

Port vertical-specific differences deliberately:

- Business should bring forward domain/validation modules.
- Baby should bring forward family/taste alignment and meaning-heavy presentation.
- Character should bring forward lore/genre/world-fit presentation.

### Phase 4: Visual QA And Regression Tests

Every migrated vertical should have:

- Desktop and mobile screenshots.
- Route smoke tests.
- No broken asset tests.
- No duplicate summary-field leakage.
- No internal/plumbing copy in UI.
- Reaction state and chosen-link persistence tests.
- Content-quality review focused on whether the page helps a user decide.

## Acceptance Criteria

A platform migration is not complete just because the route works.

It is complete when:

- The mature structure from the old vertical app is represented in the new platform.
- The shared engine remains underneath it.
- The user-facing page does not expose internal implementation terms.
- The UI helps users choose, not merely browse.
- Existing visual assets and interaction patterns are preserved unless intentionally replaced.
- Mobile and desktop screenshots look at least as complete as the legacy version.

## Immediate Next Move

Before adding new visual polish, bring Pet closer to legacy parity:

1. Port live brief and taste history.
2. Upgrade result cards with fit preview and richer reaction controls.
3. Restore native share/copy behavior from the legacy chosen/share templates.
4. Add the name detail page.
5. Then restore original-name mode.

