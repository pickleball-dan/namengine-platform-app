# NamEngine Product Vertical Launch QA - 2026-07-08

## Launch stance

Product should follow the shared NamEngine vertical template, with Pet and Business as the current visual/interaction standard.

## Product lane

- Audience: makers, founders, product teams
- Naming job: product names that work on packaging, listings, and first impressions
- Tone: tactile, polished, shelf-ready
- Core signals: Shelf clarity, Buyer appeal, Launch risk

## Asset contract

- Canonical logo: `static/images/product/namengine-product-logo.png`
- Share image: `static/images/product/namengine-product-share.png`
- Product no longer uses the temporary root-level SVG placeholders.
- Logo should remain a transparent RGBA PNG with transparent corners, a NamEngine family mark, and visible `NamEngine Product` lockup.

## Template parity checks

- Product is exported from `namengine.verticals` alongside Pet, Baby, Business, and Character.
- `/product` uses the shared intake template and visual config copy.
- `/product/results` uses Product result labels, Product validation modules, and Product fallback metadata.
- Product includes taste history like Pet, Baby, and Business.

## Local gate before push

Run locally before any deployment push:

```powershell
git status --short
$env:NAMENGINE_DB_PATH="$env:TEMP\namengine_product_readiness_test.sqlite3"; python -m unittest discover -s tests -p "test_phase16_vertical_ui_contract.py" -v
$env:NAMENGINE_DB_PATH="$env:TEMP\namengine_phase1_contract.sqlite3"; python -m unittest discover -s tests -p "test_phase1_contract.py" -v
```

For release approval, also capture screenshots for:

- `/`
- `/pet`
- `/business`
- `/product`
- `/product/results?product_description=Reusable+hydration+bottle&category=Drinkware&audience=Everyday+consumers&style=Clear+and+shelf-ready&sales_channel=Retail+shelf`

## Open items

- Confirm Product screenshots against Pet/Business after final local patch.
- Do not push until local gate and screenshot smoke are green.
