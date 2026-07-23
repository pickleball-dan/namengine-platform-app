# Deploy Bucket

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
