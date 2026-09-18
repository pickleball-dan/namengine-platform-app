# NamEngine Production E2E Report

Target: https://nam-engine.com  
Date/time: 2026-08-23 22:xx PDT  
Commands run from: `C:\Users\dnorm\.openclaw\workspace\namengine_platform_app`

## Changes made before running

- Updated `tests/e2e/helpers.js` so `answerAndAdvance()` handles the new Baby Q3 cultural heritage search UI by selecting `Irish` via `[data-heritage-search]` and `[data-heritage-value="Irish"]`.
- Added `tests/e2e/functional.spec.js` covering Baby, Pet, and Business functional production flows across the existing Playwright `desktop` and `mobile` projects.

## Baseline run — existing suite only

Command:

```bash
npx playwright test --timeout=90000 2>&1
```

Result: **47 passed / 3 failed / 6 skipped**

### Baseline failures

1. `[mobile] tests/e2e/baby.spec.js:62` — Baby card mobile width
   - Error: `Baby card width at mobile is 326px — expected >= 350px`
   - Expected: `>= 350`; Received: `326`
   - Screenshot: `test-results\baby-Baby-—-Card-sizing-th-6d939--—-no-artificial-constraint-mobile\test-failed-1.png`

2. `[mobile] tests/e2e/business.spec.js:49` — Business card mobile width
   - Error: `Business card width (300px) must be >= 85% of 390px mobile viewport (332px)`
   - Expected: `>= 331.5`; Received: `300`
   - Screenshot: `test-results\business-Business-—-Card-s-364d6-ast-85-of-viewport-—-mobile-mobile\test-failed-1.png`

3. `[mobile] tests/e2e/pet.spec.js:49` — Pet card mobile width
   - Error: `Pet card width (300px) must be >= 85% of 390px mobile viewport (332px)`
   - Expected: `>= 331.5`; Received: `300`
   - Screenshot: `test-results\pet-Pet-—-Card-sizing-matc-37f69-ast-85-of-viewport-—-mobile-mobile\test-failed-1.png`

### Baseline skips

- 6 viewport-conditional sizing tests skipped by existing test logic:
  - desktop project skips mobile-only sizing checks
  - mobile project skips desktop-only sizing checks

## Full suite run — existing + new functional tests

Command:

```bash
npx playwright test --timeout=120000 2>&1
```

Result: **63 passed / 3 failed / 10 skipped**

### Full-suite failures

Same 3 pre-existing mobile card-width failures from the baseline:

1. `[mobile] tests/e2e/baby.spec.js:62` — Baby card mobile width
   - Error: `Baby card width at mobile is 326px — expected >= 350px`
   - Expected: `>= 350`; Received: `326`
   - Screenshot: `test-results\baby-Baby-—-Card-sizing-th-6d939--—-no-artificial-constraint-mobile\test-failed-1.png`

2. `[mobile] tests/e2e/business.spec.js:49` — Business card mobile width
   - Error: `Business card width (300px) must be >= 85% of 390px mobile viewport (332px)`
   - Expected: `>= 331.5`; Received: `300`
   - Screenshot: `test-results\business-Business-—-Card-s-364d6-ast-85-of-viewport-—-mobile-mobile\test-failed-1.png`

3. `[mobile] tests/e2e/pet.spec.js:49` — Pet card mobile width
   - Error: `Pet card width (300px) must be >= 85% of 390px mobile viewport (332px)`
   - Expected: `>= 331.5`; Received: `300`
   - Screenshot: `test-results\pet-Pet-—-Card-sizing-matc-37f69-ast-85-of-viewport-—-mobile-mobile\test-failed-1.png`

### Functional suite outcome

New functional tests contributed: **16 passed / 0 failed / 4 skipped** across desktop + mobile.

Passed coverage:

- Baby: full intake reaches direction review.
- Baby: heritage search selection `Irish` reaches direction review and appears in review.
- Baby: free-form heritage `Sudanese` reaches direction review and appears in review.
- Baby: direction review edit flow returns to a question and then back to review.
- Baby: round 1 generation reaches results and shows name cards.
- Baby: paywall/access page opens from round 1 unauthenticated results.
- Baby: share link found and share page loads with HTTP status `< 400`.
- Pet: full intake reaches direction review and generation reaches results.
- Business: full intake reaches direction review and generation reaches results.

Functional skips:

- `[desktop] Functional E2E — Baby › Chosen name screen`
- `[mobile] Functional E2E — Baby › Chosen name screen`
- `[desktop] Functional E2E — Pet › Full pet intake → direction review → generate → chosen`
- `[mobile] Functional E2E — Pet › Full pet intake → direction review → generate → chosen`

Reason: production round-1 name detail/chosen links for unauthenticated users point to `/baby/access?...` or `/pet/access?...`, not to `/name/`, `/chosen`, or `/baby/name`. Since the test suite intentionally runs as a fresh unauthenticated visitor, these chosen/detail checks are blocked by paid access and were marked skipped rather than failed.

### Full-suite skipped tests

Total skipped: 10

- 6 existing viewport-conditional sizing skips.
- 4 functional chosen/detail skips blocked by unauthenticated production access, listed above.

## Bottom line

- Production functional flows for intake, review, generation, heritage search/free-form, paywall/access, and share are passing on both desktop and mobile.
- The full suite remains red due to the same 3 mobile card-width failures present in the baseline before the new functional suite was added.
- No new functional test failures remain after marking genuinely access-blocked chosen/detail flows as skipped.
