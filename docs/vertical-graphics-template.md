# NamEngine Vertical Graphics Framework

Pet is the visual standard. New verticals should feel distinct, but every vertical must still read as NamEngine: calm, intelligent, warm, refined, simple, emotionally aware, and discovery-focused.

This framework is the reusable graphics system for launching Baby, Pet, Business, Character, Product, and future naming verticals without redesigning from scratch.

## Core Principle

Each vertical gets its own emotional lane, motif, accent palette, and illustration cue. The layout, component behavior, asset slots, spacing, typography hierarchy, and mobile rhythm stay shared.

Good vertical design should answer two questions quickly:

- What kind of naming problem am I solving?
- Why does this still feel like NamEngine?

## Vertical Design Brief

Define these fields before creating assets or CSS:

```yaml
vertical_name: Baby
object_label: baby name
emotional_tone: tender, thoughtful, future-facing
primary_audience: expecting parents and naming partners
color_direction: soft blue, blush, clean white
illustration_theme: keepsake blanket, gentle baby mark, embroidered name
hero_headline_style: emotionally direct, not clever
background_motif: soft paper, nursery keepsake, subtle woven texture
result_card_design: refined editorial card with practical validation
supporting_visual_elements: initials, blanket fold, family-fit chips
```

## Brand Constants

These do not change per vertical:

- Display type: `Cormorant Garamond` for emotional headlines and section legends.
- UI type: `Inter` for forms, navigation, buttons, validation, and dense labels.
- Corner radius: default to `8px` or less.
- Header logo slot: compact `42x42` icon plus `NamEngine` text unless a special override has passed visual QA.
- Home card logo slot: compact `38x38`.
- Result reactions: three primary reactions only: Love, Maybe, No.
- Layout rhythm: mobile-first, with desktop as a wider version of the same flow.
- Tone: clear and useful, never gimmicky or over-explained.

## Theme Variables

Each vertical config should provide these core variables:

```python
theme={
    "accent": "#2f9486",
    "accent_deep": "#26364d",
    "accent_pet": "#fcba76",
    "accent_soft": "rgba(47, 148, 134, 0.14)",
    "accent_warm_soft": "rgba(252, 186, 118, 0.26)",
    "surface": "rgba(255, 252, 247, 0.95)",
    "page": "#fff1df",
    "card": "#fffcf7",
    "ink": "#1f2430",
    "muted": "#656b75",
    "line": "rgba(69, 48, 34, 0.11)",
}
```

Variable intent:

- `accent`: primary vertical color for section rails, focus, links, and selected states.
- `accent_deep`: headline and high-emphasis brand color.
- `accent_pet`: secondary warm accent. Keep the historical key name for compatibility, even outside Pet.
- `accent_soft`: subtle wash for section backgrounds.
- `accent_warm_soft`: warm or emotional wash for secondary sections.
- `surface`: main form, panel, and disclosure background.
- `page`: full-page background.
- `card`: repeated item background.
- `ink`: primary text.
- `muted`: secondary text.
- `line`: borders and quiet dividers.

Palette rules:

- Use at least two color families: a grounding color and a warm/emotional counterpoint.
- Avoid one-note monochrome palettes.
- Avoid dominant purple-blue gradients, beige-only pages, and heavy dark slate unless the vertical explicitly calls for them.
- Keep backgrounds light enough for long mobile sessions.
- Validation colors should remain standard for recognition.

## Asset Slots

Default slots:

- `logo`: canonical transparent PNG used by the compact header icon, home-card icon, intake hero, results hero, identity preview, and chosen/share moments.
- `share_image`: large social metadata image for Open Graph and Twitter cards.

Avoid these unless there is a documented reason:

- `header_logo`
- `card_logo`
- `page_logo`

If a vertical needs one of those overrides, add:

- a test explaining why,
- CSS size caps,
- screenshots for `/`, `/<vertical>`, and `/<vertical>/results`,
- comparison against Pet.

## Canonical Logo

Match the Pet canvas behavior:

- Transparent RGBA PNG.
- Square-ish canvas with transparent corners.
- Full NamEngine mark plus vertical word visible inside the canvas.
- No baked white rectangle.
- No screenshot crop as a source asset.

Rendered size checks:

- Header icon: `42x42`.
- Home card icon: `38x38`.
- Page hero: about `300px` wide on desktop and `72vw` max on mobile.
- Results hero small: about `220px` wide.

## Hero Section

Structure:

- Compact site header.
- Vertical logo first.
- Eyebrow: `NamEngine <Vertical>`.
- H1: literal naming job, emotionally clear.
- One concise support paragraph.
- Primary CTA.
- Optional secondary CTA only when the vertical has a distinct workflow, such as Pet original-name mode.
- Identity preview panel.

Hero headline rules:

- Use the vertical category or literal offer in the headline.
- Do not make the H1 a slogan if the user still needs to know what the page does.
- Keep copy specific to the vertical's emotional decision.

Examples:

- Baby: `Let's shape the right baby name.`
- Pet: `Let's shape the right pet name.`
- Business: `Find a name your business can grow into.`
- Character: `Find a name that belongs in the story.`

## Background Style

Use one of these approved background patterns:

- Soft radial wash using `--page` and a quiet white highlight.
- Subtle material cue tied to the vertical, such as paper, keepsake, card stock, or notebook texture.
- Light vertical motif embedded in a panel, not floating around the page.

Avoid:

- Decorative blobs or orbs.
- Busy wallpaper.
- Stock-photo atmospheres.
- Dark, blurred, or cropped imagery when users need clarity.

## Typography Hierarchy

- H1: Cormorant Garamond, large, calm, emotionally resonant.
- Section legends: Cormorant Garamond, strong enough to scan on mobile.
- Result names: large Inter or serif only when it improves readability.
- Labels, validation, buttons: Inter with strong weight.
- No negative letter spacing.
- Do not scale font size directly with viewport width beyond existing `clamp()` hero treatment.

## Icon And Illustration Style

Icons and illustrations should be:

- Simple, warm, and object-specific.
- Derived from the vertical's naming context.
- Compatible with the NamEngine logo mark.
- Legible at compact sizes.

Examples:

- Pet: paw, callability, personality cues.
- Baby: blanket, keepsake, family-fit cue.
- Business: briefcase, spark, launch card, signal marker.
- Character: book, mask, map, genre artifact.
- Product: tag, box, shelf card, prototype sketch.

## Button And CTA Styling

Buttons stay shared:

- Dark primary button for the main action.
- Subtle secondary button when needed.
- Minimum height `48px`.
- Radius `6px`.
- Text should fit on mobile without wrapping awkwardly.
- CTA copy should be command-oriented: `Generate Baby Names`, `Compare favorites`, `Share list`.

Vertical color can support focus, borders, and selected states, but should not make every button a different color family.

## Card Layouts

Use cards for:

- Home vertical tiles.
- Result cards.
- Identity previews.
- Modals/dialogs.
- Repeated saved-history items.

Do not put cards inside cards. Page sections should be unframed layouts or full-width bands; only individual repeated items should be cards.

Result card structure:

- Result index or role.
- Name.
- Pronunciation/tagline if present.
- Why this name.
- Fit note.
- Risks or considerations.
- Validation.
- Detail link.
- Reaction row.
- Choose button.

## Question And Input Flow Graphics

Intake sections should use the Pet grouping model:

- Three grouped sections when possible.
- Numbered section markers.
- Strong section legends.
- Left rail or border color.
- Subtle per-section background shift.
- Required/Optional markers aligned with labels.

Recommended groups:

- About the subject.
- Name style.
- Fit and feeling.

Field controls remain familiar:

- Selects for bounded choices.
- Text inputs for short context.
- Textareas for nuance.
- Optional labels visible.

## Result Page Treatment

Results pages should preserve:

- Small vertical logo.
- Eyebrow.
- Round count and option count.
- Trust cue.
- Collapsible direction summary.
- Two-column desktop result grid.
- Single-column mobile result grid.
- Bottom next-list panel with 3-reaction gate.

Vertical differences belong in:

- Palette.
- Copy labels.
- Validation module labels.
- Motif in share/chosen state.
- Result-specific fields.

## Empty, Loading, And Error States

Empty states:

- Use calm recovery language.
- Explain what can happen next.
- Provide one clear action.

Loading states:

- Use the shared progress overlay.
- Keep progress copy vertical-specific.
- Use shared motion speed and panel layout.

Error states:

- Avoid technical plumbing text.
- Say what went wrong in plain language.
- Preserve the user's path back to intake or results.

## Mobile-First Responsive Behavior

Mobile is the primary design target:

- Header must stay compact.
- Primary content should begin at the same visual rhythm as Pet.
- Form controls should be full width.
- Result cards should stack.
- Validation pills may hide detail copy if space is tight.
- CTAs must remain tappable at `48px` minimum height.
- Text must not overlap or overflow buttons/cards.

Desktop should widen the same experience:

- Intake: two-column hero/form layout.
- Results: two-column cards.
- Compare: three-column cards.
- Keep maximum content width near `1120px`.

## Spacing, Radius, Shadows, Motion

Defaults:

- Page max-width: `1120px`.
- Main horizontal padding: `24px`.
- Card radius: `8px`.
- Button/control radius: `6px`.
- Panel gap: `16px` to `36px`.
- Shadows should be soft and secondary to borders.
- Animations should be short, functional, and tied to state changes.

Avoid:

- Puffy oversized cards.
- Nested card stacks.
- Heavy blur effects.
- Decorative animation unrelated to progress or feedback.

## Component Naming Conventions

Shared component classes should stay semantic:

- `.site-header`
- `.brand-logo`
- `.vertical-card`
- `.vertical-page-logo`
- `.intake-shell`
- `.intake-section`
- `.identity-preview`
- `.results-shell`
- `.result-card`
- `.bottom-next-panel`
- `.share-preview`

Vertical-specific styling should come through:

- `body.vertical-<slug>`
- CSS variables from `VerticalConfig.theme`
- vertical-specific copy/assets in `VerticalConfig`

Avoid creating `baby-*`, `pet-*`, or `business-*` layout classes unless the visual behavior is genuinely unique.

## Example Vertical Configs

Baby:

```yaml
vertical_name: Baby
emotional_tone: tender, thoughtful, future-facing
primary_audience: expecting parents
color_direction: soft blue, blush, clean white
illustration_theme: baby keepsake blanket
hero_headline_style: direct and emotional
background_motif: soft keepsake paper
result_card_design: practical parent decision card
supporting_visual_elements: family fit, pronunciation, initials, blanket embroidery
```

Business:

```yaml
vertical_name: Business
emotional_tone: credible, energetic, launch-ready
primary_audience: founders and operators
color_direction: deep blue, warm gold, clean white
illustration_theme: launch card, briefcase, signal sparkle
hero_headline_style: growth-oriented and concrete
background_motif: subtle grid or launch notes
result_card_design: brand decision card with launch risks
supporting_visual_elements: category fit, memorability, domain/social checks
```

Character:

```yaml
vertical_name: Character
emotional_tone: imaginative, precise, story-aware
primary_audience: writers and game creators
color_direction: ink, soft violet, parchment-neutral
illustration_theme: book, map, mask, genre artifact
hero_headline_style: story-fit focused
background_motif: subtle manuscript or map texture
result_card_design: story role card
supporting_visual_elements: genre fit, era, role, pronunciation
```

Product:

```yaml
vertical_name: Product
emotional_tone: clear, useful, market-ready
primary_audience: makers and product teams
color_direction: crisp green, graphite, bright neutral
illustration_theme: package tag, shelf card, prototype sketch
hero_headline_style: utility and memorability focused
background_motif: subtle product card grid
result_card_design: launch-readiness card
supporting_visual_elements: use case, category fit, risk checks, naming family
```

## Implementation Sequence

1. Write the vertical design brief.
2. Add or update the `VerticalConfig` theme and assets.
3. Use the default shared asset slots first: `logo` and `share_image`.
4. Confirm intake questions fit the three-group structure.
5. Confirm result field labels are vertical-specific.
6. Add focused UI contract tests for assets, theme, metadata, and any special overrides.
7. Capture screenshots against Pet:
   - `/`
   - `/pet`
   - `/<vertical>`
   - `/pet/results?...`
   - `/<vertical>/results?...`
8. Fix visual mismatches before product testing.
9. Run the full test suite.
10. Verify live deployment after Render rollout.

## Launch Acceptance Checklist

- Home card logo matches the Pet slot size and visual weight.
- Mobile header remains compact.
- Hero content starts at the Pet rhythm.
- Intake grouping is clear on mobile.
- Results page preserves trust cue, direction summary, reactions, and next-list flow.
- Metadata points at `share_image`.
- No internal/plumbing copy leaks into the UI.
- No required fields are accidental.
- No text overlaps, clips, or wraps awkwardly.
- Screenshot comparison is saved or summarized in docs.
- Full regression suite passes.

## Regression Rule

If a vertical wants special graphics behavior, it needs a documented reason, a screenshot comparison, and a test. Default to Pet's shared contract unless the product experience clearly improves.
