# NamEngine Intake Consistency Spec
**Status:** Approved — in progress  
**Approved:** 2026-08-19

## Goal
Make the intake experience consistent across Baby, Pet, and Business.
Same rhythm. Same interaction model. Different voice per vertical.

## Implementation order
1. **Pet** — first (Baby is the gold standard; do not touch it)
2. **Business** — second
3. **Baby additions only** — last (Skip→Next, gentle prompts, Your direction review)

## Ironclad constraints
- No question changes (any vertical)
- No question order changes
- No existing copy/text changes (labels, help text, option text stay as-is)
- No font changes
- No color changes
- No field name changes
- No result-input changes
- Local only until visual review and explicit approval
- No deploy until Sir Dingo says go
- Baby is frozen — do not edit Baby files during Pet/Business phases

## What changes — flow model
1. One question at a time (Pet + Business conversion; Baby already done)
2. Back / Next everywhere
3. No Skip anywhere — Next on blank optional = continue without answer
4. Progress indicator for Pet and Business
5. Final "Your direction" review before generation — all answers shown, each editable
6. Edit from final review returns to that question, then back to review after Next

## What changes — gentle encouragement
Per question, new soft copy (does not change existing labels/help text):

| Trigger | Copy style |
|---|---|
| Optional question shown | Soft helper line below question |
| Required choice selected → auto-advance | Brief warm confirmation flash |
| Optional choice → Next tapped (with selection) | Warm confirmation flash |
| Text question → Next with content | "That's helpful..." confirmation |
| Text question → Next with empty field | Neutral "No worries..." or silent |

### Voice per vertical
- **Baby:** warm, emotional, thoughtful
- **Pet:** playful, personality-led, warm
- **Business:** confident, strategic, clear

### What we do NOT do
- No praise for blank/skipped answers
- No pressure messaging
- No "you should fill this in" framing
- No adding questions
- No changing existing helper text or option text

## Technical approach
- New file `static/js/pet-intake-guided.js` for Pet — never touches Baby's JS
- New file `static/js/business-intake-guided.js` for Business — separate
- Template: add `{% elif vertical.slug == "pet" %}` branch — Baby's `{% if %}` branch unchanged
- CSS: additive only, scoped under `.vertical-pet` / `.vertical-business`
- `pet-choice-cards.js` stays in place — handles visual selection state
- New guided JS listens for `change` events on native controls for auto-advance logic
- All native form inputs remain in DOM — form submits correctly

## Review gates
- After Pet: screenshots of mobile + desktop, click-through confirmation, explicit go-ahead
- After Business: same
- After Baby additions: same
- No commit without screenshots attached and reviewed
