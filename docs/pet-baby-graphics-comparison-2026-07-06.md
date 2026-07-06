# Pet vs Baby Graphics Comparison

Pet is the standard for compact header rhythm, home-card logo slots, page logo treatment, and results-page spacing.

## Findings Before Fix

- Mobile header: Pet rendered a 42x42 logo plus `NamEngine`; Baby rendered a 150x136 wordmark and pushed every page section down.
- Home grid: Pet card logo rendered in the standard 38x38 slot; Baby rendered as a 138x125 wordmark, visually overpowering the other cards.
- Baby intake page: first form column started at y=1179 on mobile versus Pet at y=1224, but Baby had fewer fields; the difference came from a much taller header and different logo slot behavior, not content quality.
- Baby results page: results grid started at y=859 on mobile versus Pet at y=781, with most of the extra offset caused by the oversized Baby header.

## Fix

- Removed Baby-only `header_logo`, `card_logo`, and `page_logo` overrides.
- Baby now follows Pet's default `logo` + `share_image` asset contract.
- Capped optional wordmark slot rendering in CSS so future overrides cannot inflate compact header/card slots.
- Added a durable graphics template at `docs/vertical-graphics-template.md`.

## Measurements After Fix

- Header logo: Pet 42x42, Baby 42x42.
- Home-card logo: Pet 38x38, Baby 38x38, Business 38x38, Character 38x38.
- Desktop intake alignment: Pet form y=150, Baby form y=150.
- Mobile page logo y-position: Pet y=163, Baby y=163.
- Mobile results hero logo y-position: Pet y=163, Baby y=163.
- Baby mobile results grid moved from y=859 to y=765.
