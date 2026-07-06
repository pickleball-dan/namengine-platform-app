# NamEngine Vertical Graphics Template

Pet is the baseline graphics contract for new verticals.

## Asset Slots

- `logo`: canonical transparent PNG used by the compact header icon, home-card icon, intake hero, results hero, identity preview, and chosen/share moments.
- `share_image`: large social metadata image for Open Graph and Twitter cards.
- Avoid `header_logo`, `card_logo`, and `page_logo` unless a vertical has a proven reason and has passed screenshot review in every slot.

## Canonical Logo

- Match the Pet canvas style: transparent RGBA PNG, square-ish canvas, transparent corners.
- Keep the full NamEngine mark and vertical word visible inside the canvas.
- Do not bake in white or tinted rectangular backgrounds.
- Check the logo at these rendered sizes:
  - Header icon: 42x42.
  - Home card icon: 38x38.
  - Page hero: about 300px wide on desktop and 72vw max on mobile.
  - Results hero small: about 220px wide.

## Share Image

- Use a dedicated large image optimized for metadata previews.
- It should include the vertical wordmark and a simple visual cue.
- Verify the rendered page includes the share image in `og:image`.

## Screenshot Checklist

Capture Pet and the target vertical together before shipping:

- `/` desktop: target vertical card logo should not be taller or visually heavier than Pet.
- `/<vertical>` mobile: compact header should match Pet's header rhythm and not push the hero down.
- `/<vertical>` desktop: page hero, identity preview, and intake form should align with Pet's proportions.
- `/<vertical>/results?...` mobile: results heading should begin at the same visual height as Pet for equivalent content.
- Metadata: `og:image` should point to the vertical share image, not the raw logo.

## Regression Rule

If a vertical wants special slot overrides, add an explicit test explaining why the override exists and what size cap protects it. Default to the Pet slot contract.
