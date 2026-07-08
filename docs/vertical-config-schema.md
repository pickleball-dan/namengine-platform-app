# NamEngine VerticalConfig Visual Contract

This is the implementation-facing contract for launching new Namegine / NamEngine naming verticals without redesigning the app shell.

Pet remains the visual standard. Mobile remains the primary target.

## Goal

Every vertical should share:

- page frame
- header rhythm
- hero layout
- intake structure
- results flow
- button system
- card system
- state handling

Every vertical may customize:

- emotional tone
- palette
- background motif
- icon direction
- illustration direction
- hero copy
- result-card flavor

## Live schema

`VerticalConfig` now includes a typed `visual` block via `VerticalVisualConfig` in `namengine/core/schemas.py`.

```python
@dataclass(frozen=True, slots=True)
class VerticalVisualConfig:
    audience: tuple[str, ...] = ()
    emotional_tone: tuple[str, ...] = ()
    main_colors: tuple[str, ...] = ()
    accent_colors: tuple[str, ...] = ()
    background_style: str = ""
    icon_style: str = ""
    illustration_style: str = ""
    hero_message: str = ""
    hero_support: str = ""
    identity_statement: str = ""
    identity_points: tuple[str, ...] = ()
    result_card_style: str = ""
```

## Required fields for new verticals

The UI contract validates these `visual` fields:

- `audience`
- `emotional_tone`
- `main_colors`
- `accent_colors`
- `background_style`
- `icon_style`
- `illustration_style`
- `hero_message`
- `result_card_style`

## What each field controls

### `audience`
Who the vertical is for. Useful for product copy and future onboarding nuance.

### `emotional_tone`
Three-ish words that keep the art direction emotionally coherent.

### `main_colors`
The grounding colors for the vertical. These should align with the actual theme tokens.

### `accent_colors`
Warm or contrast accents that keep the screen from feeling one-note.

### `background_style`
A short description of the approved page/background treatment.

### `icon_style`
A short direction for icon shape, warmth, and specificity.

### `illustration_style`
The hero/supporting illustration direction.

### `hero_message`
The literal H1 used on the intake page.

### `hero_support`
Optional support copy under the H1. Defaults to `prompt_context` if omitted.

### `identity_statement`
Optional preview-panel headline.

### `identity_points`
Optional preview-panel chips/checkpoints.

### `result_card_style`
A short name for the intended result-card flavor. Used as a durable design label and exposed in the results DOM for future styling hooks.

## Baby reference implementation

The canonical Baby implementation now lives in `namengine/verticals/configs.py`.

Reference shape:

```yaml
vertical_name: Baby
visual:
  audience:
    - expecting parents
    - naming partners
  emotional_tone:
    - tender
    - thoughtful
    - future-facing
  main_colors:
    - "#7d95c7"
    - "#29344f"
  accent_colors:
    - "#f0b8c8"
    - "#f7fbff"
  background_style: soft keepsake paper with a breathable nursery wash
  icon_style: soft-outline keepsake cues with rounded detail
  illustration_style: editorial minimal with blanket and embroidery motifs
  hero_message: Let’s shape the right baby name.
  hero_support: Generate baby names with warmth, pronunciation clarity, cultural care, and enough explanation to help parents judge fit.
  identity_statement: Built for names that feel tender now and substantial later.
  identity_points:
    - Sound
    - Style
    - Family fit
  result_card_style: practical parent decision card
```

## How future verticals should use this

1. Start from the shared app shell. Do not redesign layout first.
2. Fill out the `visual` block before making assets.
3. Keep `theme` colors and `visual.main_colors` / `visual.accent_colors` aligned.
4. Write the hero copy from the naming job, not from a slogan.
5. Keep the preview panel specific to the real decision criteria.
6. Reuse `logo` and `share_image` slots unless there is a documented exception.
7. Compare the new vertical against Pet on mobile before polish passes.

## Minimal implementation recipe

For a new vertical:

1. Add the `VerticalConfig` entry in `namengine/verticals/configs.py`
2. Fill in `theme`, `assets`, and `visual`
3. Add intake questions using the shared 3-section structure when possible
4. Add result labels and validation modules
5. Run `python -m unittest discover -s tests`
6. Capture mobile screenshots against Pet before launch
