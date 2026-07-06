# Business Vertical Launch Notes

Business uses the shared NamEngine vertical framework with Pet as the visual
standard. The page should feel credible, energetic, and launch-ready while
staying calm, refined, and discovery-focused.

## Design Brief

- Vertical name: Business
- Object label: business name
- Primary audience: founders, operators, and small business owners
- Emotional tone: credible, energetic, launch-ready
- Color direction: deep blue, warm gold, clean white
- Illustration theme: launch card, briefcase, signal sparkle
- Hero headline: Find a name your business can grow into.
- Background motif: subtle launch notes or grid
- Result-card direction: brand decision card with launch risks

## Graphics Contract

Business uses the standard shared asset slots:

- `logo`: `images/business/namengine-business-logo.png`
- `share_image`: `images/business/namengine-business-share.png`

No `header_logo`, `card_logo`, or `page_logo` overrides are used. The compact
header, home-card, intake hero, and results hero should follow the same slot
behavior as Pet and Baby.

## Intake Structure

Business uses three launch-decision sections:

- About the business
- Name style
- Launch fit

Required signals:

- `business_description`
- `audience`
- `style`

The intake should capture enough context to judge category fit, audience fit,
memorability, naming style, domain/handle constraints, and avoid-list concerns.

## Results Treatment

Business result cards use these vertical-specific labels:

- Positioning hint
- Why this name?
- Brand fit
- Launch risks

Validation modules:

- Domain signal
- Category fit
- Launch risk
- Avoid list, when supplied

These checks are directional product QA. They do not replace legal, trademark,
domain, or social-handle review.

## Domain Quick Check

Business results include a compact domain quick-check panel when names are
generated. The panel shows one practical display domain, a GoDaddy-derived
availability badge when credentials are configured, and this fixed disclaimer:

`Quick GoDaddy check, not guaranteed. Verify before purchase.`

Runtime configuration:

- `GODADDY_API_KEY`
- `GODADDY_API_SECRET`
- `GODADDY_API_BASE`, optional, defaults to `https://api.godaddy.com`
- `GODADDY_TIMEOUT_SECONDS`, optional, defaults to `4`
- `DOMAIN_CACHE_PATH`, optional, defaults beside `NAMENGINE_DB_PATH`
- `DOMAIN_CACHE_TTL_SECONDS`, optional, defaults to six hours
- `DOMAIN_UNKNOWN_CACHE_TTL_SECONDS`, optional, defaults to fifteen minutes

When GoDaddy credentials are missing, results still render with `Not checked`
instead of blocking generation.

## QA Checklist

- `/business` uses the Business logo and share image.
- `/business` H1 is growth-oriented and literal.
- `/business` renders three grouped intake sections.
- `/business/results` shows Business fallback names when AI is unavailable.
- Business results do not show pet or baby fallback copy.
- Business validation does not show `validation_not_configured`.
- Business result cards show the domain quick-check panel and disclaimer.
- Header logo remains compact like Pet.
- Home card logo remains in the shared `38x38` slot.
- Full regression suite passes.
