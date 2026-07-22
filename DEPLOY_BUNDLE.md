# Deploy Bundle Tracker

Purpose: track local NamEngine changes that should be reviewed, verified, and pushed together to reduce Render deploys.

## Current bundle: pending

### Ready / likely in scope

- [x] Baby chosen keepsake/portrait placeholder overflow fix
  - File: `static/css/platform.css`
  - Reason: selected baby names could overflow the keepsake card because the shared `.portrait-monogram` rule overrode the smaller blanket name sizing.
  - Fix: added a more specific `.baby-keepsake-placeholder .blanket-embroidered-name` rule to cap width, restore clamped sizing, and allow safe wrapping.
  - Verification: `python -m pytest tests/test_phase6_chosen.py -q` passed: 14 passed.
  - Status: local fix made; needs local visual review before bundled push.

- [x] Baby results saved-progress round clarity fix
  - Files: `app.py`, `templates/results.html`, `static/js/reactions.js`, `tests/test_phase7_refinement.py`, `tests/test_baby_flow_polish_v1.py`, `tests/test_baby_ui_consistency.py`
  - Reason: Round 2+ copy said “You loved 0 names in Round 2,” which was technically current-round data but looked like it contradicted prior-round love reactions used for refinement.
  - Fix: Round 2+ now says the list was shaped by loved names from the previous round and separately shows loved names in the current round so far; live reaction updates preserve that context.
  - Verification: `python -m pytest tests/test_phase7_refinement.py tests/test_baby_flow_polish_v1.py tests/test_baby_ui_consistency.py -q` passed: 22 passed.
  - Status: local fix made; needs local visual review before bundled push.

- [x] Baby generation teddy/progress phase visibility fix
  - Files: `static/js/progress.js`, `static/css/platform.css`
  - Reason: phase 1/2 of the name-generation overlay could appear visually static/generic; Baby detection depended too much on submitted fields.
  - Architecture: shared progress JS now detects the active vertical and exposes `data-progress-phase`; Baby styles consume that shared phase state for teddy/bubble motion.
  - Verification: intercepted local Playwright run confirmed phase 1 → 2 → 3 labels/classes advance without hitting `/baby/results`; `tests/test_phase14_progress_experience.py` passed.

- [x] Generation overlay one-line active progress fix
  - Files: `static/css/platform.css`, `tests/test_phase14_progress_experience.py`
  - Reason: the full five-step progress list was redundant with the bold headline and could be cut off on mobile.
  - Fix: keep the existing progress markup/logic but visually display only the active step line.
  - Verification: `python -m pytest tests/test_phase14_progress_experience.py -q` passed: 9 passed.

- [x] Baby teddy thinking bubbles visibility/progression fix
  - Files: `static/css/platform.css`, `static/js/progress.js`, `tests/test_phase14_progress_experience.py`
  - Reason: teddy-bear thinking bubbles were too faint and did not feel more active as generation progressed; active progress message color read too red/coral.
  - Fix: strengthened bubble contrast, added a fuller bubble cluster, exposed `data-progress-phase` from progress JS so later phases show denser bubbles, and changed the active Baby progress message/dot to green.
  - Verification: `python -m pytest tests/test_phase14_progress_experience.py -q` passed: 9 passed.

### Ready / likely in scope

- [x] Chosen keepsake portrait polling cleanup
  - Files: `templates/chosen.html`, `tests/test_phase6_chosen.py`
  - Reason: `/api/chosen/<id>/portrait` polled roughly every 2 seconds while waiting; not a major cost leak, but operationally noisy.
  - Fix: client polling now uses a short backoff sequence, stops calmly after fewer checks, clears the polling URL on ready/failed/timeout, and resets polling state on retry.
  - Verification: `python -m pytest tests/test_phase6_chosen.py -q` passed: 14 passed.

### Proposed / not yet implemented

- [ ] Avoid server-side requeueing from portrait status polling unless stale
  - Files likely: `app.py`, maybe image metadata helpers
  - Reason: status polling can still call the queue guard for pending portraits; the in-memory job guard prevents duplicate jobs, but a future cleanup could make stale requeue semantics explicit.
  - Suggested fix: add safe pending-age metadata or a server-side stale check without mixing unrelated telemetry leftovers.

### Needs verification before push

- [ ] Local visual review at `http://127.0.0.1:5307/`
- [ ] Cross-vertical architecture review: confirm Baby improvements are implemented as shared patterns/utilities where practical, not Baby-only one-offs.
- [ ] Check Pet/Business/other relevant verticals for regressions when a shared shell/component changes.
- [ ] Confirm exact staged file list before commit
- [ ] Run focused smoke/tests for touched areas
- [ ] User approval before push to `main`

## Cross-vertical architecture rule

- Baby can be the design/proofing lab, but reusable work should graduate into shared vertical patterns.
- Prefer shared templates, shared CSS classes/tokens, shared JS helpers, and vertical config overrides over duplicated Baby-only code.
- Keep vertical-specific styling only when the behavior or brand treatment truly needs to differ.
- Before pushing Baby work, ask: “Should this also apply to Pet, Business, Product, Book, or future verticals?”

## Hard rules

- Do not push one-off UI fixes immediately unless explicitly urgent.
- Bundle deploy-worthy fixes into one scoped commit when practical.
- Never include unrelated local/experimental changes in the bundle.
- Before pushing, list exact files to be staged and get approval.
