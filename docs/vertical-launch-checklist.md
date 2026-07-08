# NamEngine Vertical Launch Checklist

Use this when adding a new naming vertical.

## 1. Config contract

- [ ] `VerticalConfig.slug` added
- [ ] `display_name`, `object_label`, `route_prefix` set
- [ ] `theme` filled in
- [ ] `assets.logo` set
- [ ] `assets.share_image` set
- [ ] `visual.audience` set
- [ ] `visual.emotional_tone` set
- [ ] `visual.main_colors` set
- [ ] `visual.accent_colors` set
- [ ] `visual.background_style` set
- [ ] `visual.icon_style` set
- [ ] `visual.illustration_style` set
- [ ] `visual.hero_message` set
- [ ] `visual.result_card_style` set

## 2. Intake flow

- [ ] Uses shared structure rhythm
- [ ] Sections are grouped clearly
- [ ] At least one strong required signal per critical section
- [ ] Labels are user-facing, not internal/plumbing language
- [ ] Mobile inputs are full width
- [ ] Optional fields are clearly marked

## 3. Hero + preview panel

- [ ] H1 says the real naming job
- [ ] Support copy is calm and specific
- [ ] Preview panel statement is vertical-specific
- [ ] Preview panel points reflect actual decision criteria
- [ ] CTA reads naturally on mobile

## 4. Results

- [ ] Result labels are vertical-specific
- [ ] Validation language fits the vertical
- [ ] Reaction row still uses Love / Maybe / No
- [ ] Bottom next-list panel still works unchanged
- [ ] Empty/loading/error states have plain-language copy

## 5. Graphics and assets

- [ ] Uses shared `logo` slot
- [ ] Uses shared `share_image` slot
- [ ] No `header_logo`, `card_logo`, or `page_logo` override unless documented
- [ ] Background treatment is quiet, light, and mobile-safe
- [ ] Icons match the stated icon style
- [ ] Illustration style feels like the same Namegine family

## 6. QA

- [ ] Compare against Pet on mobile
- [ ] Header stays compact
- [ ] Hero rhythm matches shared system
- [ ] No text overflow or clipped buttons
- [ ] Result cards stack cleanly on mobile
- [ ] Home card feels visually balanced with the other verticals
- [ ] `python -m unittest discover -s tests` passes
