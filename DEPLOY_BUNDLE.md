# Deploy Bucket

## Cross-vertical paid-access refinement gate bundle

Status: ready for validation/push
Branch: current working tree / next local-first release batch

Included intent:
- Generalize the existing Stripe Payment Link wrapper to every active naming vertical via `/<vertical>/access` while keeping legacy `/<vertical>/beta` routes as internal/backward-compatible aliases.
- Keep the full first intake, first generated list, and Love/No reactions free for Baby, Pet, Business, and future verticals.
- Replace the free second-list/refinement form with one centered paid-access unlock panel.
- Remove the duplicate lower paid-access CTA from the secondary action row.
- Offer a clear 100% money-back guarantee if NamEngine does not feel useful.
- Block free `/refine` requests server-side with a 402 paywall response for each vertical.
- Preserve the lightweight `paid=1` success-return state through access success, intake, feelings, results, and refine.
- Allow paid users to continue to an existing session when the access success page receives `return_session`.
- Use separate internal payment environment variables per vertical: `NAMENGINE_BABY_BETA_PAYMENT_LINK`, `NAMENGINE_PET_BETA_PAYMENT_LINK`, `NAMENGINE_BUSINESS_BETA_PAYMENT_LINK`, etc.
- Use separate internal display-price environment variables per vertical: `NAMENGINE_BABY_BETA_PRICE`, `NAMENGINE_PET_BETA_PRICE`, `NAMENGINE_BUSINESS_BETA_PRICE`, etc.

Expected customer-facing effect:
- Free users can try the full first list, then see a single centered “Unlock {Vertical} Access” moment.
- Each vertical has its own checkout route and payment link, so users can use Baby, Pet, and Business separately.
- The unlock CTA reads as paid access, backed by the 100% money-back guarantee.
- Paid/success-return users can generate refined lists once they have enough reactions.
- Paid users do not see any beta/risk-free CTA duplicated below Compare/Share.

Validation run:
- `python -m py_compile app.py tests/test_phase26_paid_beta_trust_wrapper.py`
- `python -m pytest tests/test_phase7_refinement.py tests/test_phase18_pet_legacy_parity.py tests/test_phase19_baby_smoke_validation.py tests/test_baby_refinement_generation_cache.py tests/test_results_mobile_stabilization_v1.py tests/test_phase26_paid_beta_trust_wrapper.py tests/test_phase14_progress_experience.py -q`
- `git diff --check`

Not included:
- Full Stripe SDK Checkout Session creation.
- Stripe webhooks or durable customer entitlement storage.
- Login/account-based access control.
- Automated refund processing workflow.
- Free-intake field restrictions.

## Open text character-limit polish bundle

Status: ready for validation/push
Branch: current working tree / next local-first release batch

Included intent:
- Add visible `maxlength` attributes to NamEngine open text fields so users are guided before submit.
- Keep the full first-intake/free-list experience intact; this is polish and cost-control, not a paywall change.
- Cap custom “Other” inputs at 120 characters and refinement instructions at 200 characters.
- Use field-specific limits for richer context fields such as family context, notes, pet details, business/product descriptions, and partner-alignment text.
- Trim server-side refinement instructions to the same 200-character limit as the UI.

Expected customer-facing effect:
- Open text boxes stop accepting oversized entries in the browser.
- The refinement direction field stays short and focused.
- Existing first-list generation flow remains unchanged.

Validation run:
- `python -m py_compile app.py`
- `python -m pytest tests/test_baby_conversational_intake_v1.py tests/test_phase16_vertical_ui_contract.py -q`
- `git diff --check`

Not included:
- Paid/refinement gating implementation.
- Choice-only free-intake restrictions.
- Backend intake schema limit changes beyond refinement instruction trimming.

## Baby progress overlay refinement bundle

Status: ready for validation/push
Branch: feature/baby-progress-overlay-current-main

Included intent:
- Keep Baby teddy/bubbles treatment during Round 2+ refinement progress.
- Hide the visible Baby progress status line while preserving progress behavior for timing, fetch, redirect, animation phase, and accessibility.
- Remove user-facing “shortlist” wording from active NamEngine product/progress copy touched by this bundle; keep internal route/class/function identifiers intact to avoid breaking share behavior.
- Simplify Baby detail-page reactions by removing the visible “Keep as a maybe” choice; new customer-facing reactions are Love or Not for us only.

Expected customer-facing effect:
- Baby initial generation and refinement use the teddy/bubbles overlay.
- Baby overlay no longer shows the green status line.
- Naming copy uses “names,” “favorites,” “saved-name,” or “final names” instead of the banned wording.
- Baby name detail pages show only “Love this name” and “Not for us,” reducing indecision clutter.

Validation to run before push:
- node --check static/js/progress.js
- git diff --check
- python -m pytest tests/test_phase14_progress_experience.py tests/test_baby_conversational_intake_v1.py tests/test_baby_flow_polish_v1.py tests/test_baby_ui_consistency.py -q

Not included:
- test-results/
- temp/
- artifacts/
- .env or secret files
- route/function/class renames for shared saved-name pages

## Full Report underline/focus polish

Status: validated locally / included in next push
Branch: current working tree / next local-first release batch

Included intent:
- Restore the visual underline/line treatment beneath the `Full Report` action on result cards.
- Keep the current `Full Report →` CTA copy and locked-card behavior intact.
- Preserve the shared Baby/Pet/Business result-card contract; this should be CSS polish only unless inspection proves otherwise.
- Ensure hover/focus states remain accessible and obvious on mobile and desktop.

Expected customer-facing effect:
- `Full Report` looks intentionally tappable/clickable again instead of visually flattened.
- Locked first-run cards keep the premium access path without reintroducing `Quick view` for locked users.

Validation to run before push:
- Inspect `static/css/platform.css` around `.result-explore-link` and recent card-layout overrides.
- `python -m pytest tests/test_results_mobile_stabilization_v1.py tests/test_baby_ui_consistency.py -q`
- `git diff --check`
- Mobile + desktop screenshots for Baby/Pet/Business locked result cards.

Not included:
- Copy changes away from `Full Report →`.
- Reopening locked `Quick view` behavior.
