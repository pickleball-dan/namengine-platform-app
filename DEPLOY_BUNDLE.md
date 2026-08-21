# Deploy Bucket

## Interview UX — Progress gauge below question, Back button, header, Save & exit cleanup

Status: local-only / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Restore site header visibility during Baby interview (was hidden by CSS; now shows on all three verticals).
- Remove Back button from Q1 on all three verticals (Baby, Pet, Business); Back now appears below the question, before Next, on Q2+.
- Remove "Save & exit" from interview nav on all three verticals — Home is already in the site header.
- Baby header scroll fix: `startInterview()` now scrolls to top of page rather than form, keeping header in view.
- CSS: question-actions divs now flex-row; inline Back button styled per vertical.

Files changed:
- `templates/intake.html`
- `static/js/baby-intake-polish.js`
- `static/js/pet-intake-guided.js`
- `static/js/business-intake-guided.js`
- `static/css/platform.css`

Expected customer-facing effect:
- All three verticals show the site header during the interview.
- Back button is absent on Q1; appears below the question (before Next) on Q2+.
- No "Save & exit" link cluttering the interview nav.

Not included:
- Direction review or generation loading state changes.
- Mobile layout changes.

## Pet question card artifact fix + choice deselect

Status: local-only / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Move `pet-play-scene` inside `pet-question-stage` so decorative elements (paw, ball, bone) are confined to the question card area and do not bleed below it.
- Fix `pet-native-submit` and `business-native-submit` — `polished-intake-form > button { min-height: 58px }` was overriding the visually-hidden CSS, making them render as visible 58px elements. Added more-specific rule with `min-height: 0 !important; opacity: 0; clip-path: inset(50%)`.
- Deselect behavior: clicking an already-selected choice card on an **optional** question now clears the selection. Required questions keep their selection. Applies to Baby, Pet, and Business via `pet-choice-cards.js` (Pet + Business) and `baby-intake-polish.js` (Baby).

Files changed:
- `templates/intake.html`
- `static/css/platform.css`
- `static/js/pet-choice-cards.js`
- `static/js/baby-intake-polish.js`

Expected customer-facing effect:
- No visible artifacts or thin black lines below pet question cards.
- Users can click a selected optional answer to deselect it.

Not included:
- Business play-scene changes (business has no equivalent play-scene).
- Required question deselect (intentionally kept selected).

## Progress overlay label removal

Status: local-only review approved for deploy bucket / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Remove the small progress-visual label pill below the orb on the non-Pet progress overlay (`Identity fit`; Baby previously rendered `Family fit` in the same element).
- Keep the animated graphic, progress copy, patience meter, and loading behavior unchanged.
- Scope the implementation to `templates/progress_overlay.html` only.

Expected customer-facing effect:
- The progress overlay graphic no longer shows the extra button-like label under the orb.
- The loading panel feels cleaner and avoids the mistaken impression that the label is an actionable button.

Validation run:
- Local Playwright mobile capture against `/business` with overlay forced visible.
- Review screenshot saved under `qa-artifacts/progress-overlay-label-removal-20260818-1048/`.
- Capture diagnostics reported `hasProgressVisualLabel: false`, `hasIdentityFitText: false`, no console errors, and no horizontal overflow.

Not included:
- Progress copy changes.
- Pet paw progress visual changes.
- CSS/layout redesign beyond removing the template label element.

## Baby rejected-candidate audit trail

Status: validated locally / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Require `rejected_candidates` in the Baby finalizer prompt contract and strict response schema.
- Bring Baby into parity with the other verticals for rejected-candidate audit metadata: `name`, `territory`, `rejection_reason`, `lost_to`, and `score_summary`.
- Preserve live result behavior: final displayed names remain separate from audit metadata; no client-facing template, CSS, or JavaScript changes.
- Keep `/dev/engine-audit` and future export/audit paths able to explain not only why finalists won, but why Baby candidates lost.

Expected quality/audit effect:
- Baby generations now retain the same finalist-vs-rejected decision trail as Pet, Business, and other verticals.
- The primary vertical no longer loses the “why did we reject X” story after the finalizer pass.
- Rejected Baby candidates can become usable backend evidence for audit, QA, and future client-facing explanation exports.

Validation run:
- `python -m unittest discover -s tests -p test_phase11_ai_generation.py`
- `python -m py_compile namengine/core/ai_generation.py app.py`
- `git diff --check -- namengine/core/ai_generation.py tests/test_phase11_ai_generation.py DEPLOY_BUNDLE.md`

Not included:
- UI/UX changes.
- Template, CSS, or JavaScript changes.
- Client-facing audit/export changes.

## Reaction-derived taste signal enrichment

Status: validated locally / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Enrich round 2/3 taste profiles with AI metadata already generated and stored on reacted names.
- Feed liked/disliked `territory` and rationale signals from matched `candidate_pool` / `rejected_candidates` rows back into the AI-facing taste profile.
- Preserve legacy first/last-letter `liked_sounds` / `disliked_sounds` compatibility, but stop treating `maybe_names` as an active AI-facing prompt signal because current product reactions do not include Maybe.
- Keep the change backend/taste-profile/test-only; no UI, UX, template, CSS, or JavaScript changes.

Expected quality effect:
- Refinement rounds can learn from actual naming territories and rationale/lane metadata instead of relying mostly on shallow letter-edge sound counts.
- Rejected names can steer away from disliked territories and tags with more precision.
- Existing stored legacy Maybe values remain readable, but new AI prompts focus on Love/No signals.

Validation run:
- `python -m unittest discover -s tests -p test_phase9_taste_profile.py`
- `python -m py_compile namengine/core/taste.py namengine/core/schemas.py namengine/core/ai_generation.py app.py`
- `git diff --check -- namengine/core/taste.py namengine/core/schemas.py namengine/core/ai_generation.py tests/test_phase9_taste_profile.py DEPLOY_BUNDLE.md`

Not included:
- UI/UX changes.
- Reaction button/layout changes.
- Prompt-pipeline restructuring.

## SQLite WAL concurrency safety

Status: validated locally / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Enable SQLite `journal_mode=WAL` at the shared storage connection boundary.
- Preserve existing `foreign_keys=ON` and `busy_timeout=5000` connection settings.
- Reduce writer/read-lock contention for reactions, taste-profile saves, session saves, and future multi-worker/multi-thread Render scaling.
- Keep the change backend/storage-only; no UI, UX, template, CSS, or JavaScript changes.

Expected production effect:
- SQLite can allow readers during writes instead of relying on rollback-journal exclusive locking behavior.
- Current single-worker behavior remains compatible while reducing a future scaling landmine.

Validation run:
- `python -m unittest discover -s tests -p test_phase5_storage.py`
- `python -m py_compile namengine/core/storage.py app.py`
- `git diff --check -- namengine/core/storage.py tests/test_phase5_storage.py DEPLOY_BUNDLE.md`

Not included:
- Worker/thread scaling changes.
- Database migration scripts.
- UI/UX changes.

## OpenAI transient retry safety

Status: validated locally / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Allow one bounded OpenAI SDK retry by default so a single transient provider/network blip does not kill the entire three-pass generation.
- Keep retries configurable with `NAMENGINE_OPENAI_MAX_RETRIES` and document production default `1` in `render.yaml`.
- Preserve the 60s OpenAI timeout floor and three-pass quality pipeline; this does not shorten generation or reduce output budget.
- Pair with the increased 420s Gunicorn headroom so the retry safety does not immediately collide with the web request timeout.

Expected customer-facing effect:
- Fewer generic generation-failure messages caused by brief network/provider interruptions during one stage.
- High-quality generations get one recovery chance instead of failing after the first transient SDK exception.

Validation run:
- `python -m unittest discover -s tests -p test_openai_timeout_fallback.py`
- `python -m py_compile namengine/core/ai_generation.py app.py`
- `git diff --check -- namengine/core/ai_generation.py tests/test_openai_timeout_fallback.py render.yaml DEPLOY_BUNDLE.md`

Not included:
- UI/UX changes.
- Prompt, model, or three-pass pipeline changes.
- OpenAI timeout reductions.
- Unbounded or app-level retry loops.

## Quality-preserving generation timeout headroom

Status: validated locally / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Preserve the three-pass OpenAI naming pipeline quality instead of shortening provider timeouts below observed Mission Control latency.
- Increase Gunicorn request headroom from 240s to 420s in `gunicorn.conf.py`, `Procfile`, and `render.yaml` so slow high-quality generations are less likely to be cut off near the end of the request.
- Keep `NAMENGINE_OPENAI_TIMEOUT_SECONDS` unchanged at 60s; this does not lower OpenAI quality budget.
- Add a focused runtime-config test that locks the Gunicorn config and start-command timeout values together.

Expected customer-facing effect:
- Users are less likely to hit a 502 after waiting for a legitimate long-running quality generation.
- Existing generation UI/UX remains unchanged in this backend/runtime bucket.

Validation run:
- `python -m unittest discover -s tests -p test_gunicorn_runtime_config.py`
- `python -m py_compile app.py namengine/core/ai_generation.py`
- `git diff --check -- gunicorn.conf.py Procfile render.yaml tests/test_gunicorn_runtime_config.py DEPLOY_BUNDLE.md`

Not included:
- OpenAI timeout reductions.
- Three-pass prompt/pipeline changes.
- Template, CSS, JavaScript, or UX copy changes.

## Dev eval report AI-default safety fix

Status: validated locally / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Make `/dev/eval-report` default to the AI-backed taste engine instead of the deterministic fallback pool.
- Preserve explicit fallback regression access with `/dev/eval-report?ai=0`.
- Keep the change backend/test-only; no UI, UX, template, CSS, or JavaScript changes.
- Prevent internal taste-separation QA from silently validating the wrong engine by default.

Expected internal effect:
- Default eval-report checks now exercise the same AI path intended to represent production taste behavior.
- Fallback-pool regression remains available only when explicitly requested.

Validation run:
- `python -m unittest discover -s tests -p test_phase23_eval_report_view.py`
- `python -m py_compile app.py namengine/core/evals.py`
- `git diff --check -- app.py tests/test_phase23_eval_report_view.py DEPLOY_BUNDLE.md`

Not included:
- UI/UX banner changes.
- Template, CSS, or JavaScript changes.

## Vertical header Home link polish

Status: validated locally / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Replace the top-left vertical header logo link on Baby, Pet, and Business pages with plain `Home` text.
- Keep the link destination as `/`, since it returns users to the main NamEngine home page.
- Preserve the main/homepage NamEngine logo in the header.
- Reduce confusion from vertical logos acting like a main-home navigation control.

Expected customer-facing effect:
- Vertical pages clearly show `Home` in the top-left when the click target goes to the main NamEngine home page.
- Baby, Pet, and Business headers behave consistently.

Validation run:
- `python -m compileall app.py namengine templates`
- Playwright local screenshot/text check on fresh Flask server: Baby/Pet/Business header brand text returned `Home`.
- Screenshots saved under `qa-artifacts/home-link-screenshots/`.

Not included:
- Footer logo changes.
- Main homepage header logo changes.
- Navigation destination changes away from `/`.

## Mission Control per-session OpenAI cost feed

Status: validated locally / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Add session-level OpenAI usage/cost rows to the NamEngine Mission Control telemetry API.
- Expose `requests_by_session` alongside the existing model, request-type, vertical, and day groupings.
- Include session id, date, vertical, model, request count, token totals, latency, generated-name count, missing-token count, and estimated spend per session.
- Remove the repeated request-type list from per-session rows so Mission Control does not show a noisy all-same column.
- Keep existing summary/model/request-type payload fields backward-compatible for the current Operations dashboard.

Expected Mission Control effect:
- The Operations OpenAI usage dashboard now has backend data available to render per-session costs below or beside the existing aggregate tables.
- The current screenshot’s “estimated cost by model” and “usage by request type” totals can be drilled down by session once the dashboard frontend consumes `requests_by_session`.

Validation run:
- `python -m pytest tests/test_mission_control_telemetry_v1.py tests/test_phase26_paid_beta_trust_wrapper.py -q`
- `git diff --check`

Not included:
- Frontend Operations dashboard rendering changes if that dashboard source lives outside this repository.
- Authentication or token changes for the internal telemetry endpoint.

## Mission Control usage exceptions/anomalies feed

Status: validated locally / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Investigate the legacy `candidate_generator_ranker_v1` request type seen in Mission Control usage distribution.
- Confirm it is historical telemetry from the older one-call / generator-ranker flow, not part of the current normal three-pass engine.
- Preserve the existing `requests_by_request_type` payload for frontend compatibility.
- Add a new `usage_exceptions` payload so Mission Control can emphasize anomalies instead of merely counting normal engine stages.
- Define the normal pipeline as `taste_interpreter_v1`, `candidate_generator_v1`, and `critic_ranker_finalizer_v1`.
- Surface unexpected request types, sessions with missing/imbalanced pipeline stages, failures by error type, and missing-token-usage rows.

Expected Mission Control effect:
- The Operations dashboard can replace or supplement “Usage by request type” with “Usage Exceptions” / “Anomalies.”
- Normal 3-stage traffic becomes baseline context instead of the main visual signal.
- Legacy or abnormal request types like `candidate_generator_ranker_v1` become easier to notice and explain.

Validation run:
- `python -m py_compile namengine/core/mission_control_telemetry.py app.py`
- `python -m pytest tests/test_mission_control_telemetry_v1.py tests/test_phase21_engine_audit.py -q`
- `git diff --check`

Not included:
- Frontend Operations dashboard UI changes to consume `usage_exceptions`.
- Removal of legacy request-type aggregate fields from the API.
- Production database cleanup or historical telemetry rewriting.

## Mission Control session-cost reporting window and sort feed

Status: validated locally / included in next release batch
Branch: current working tree / next local-first release batch

Included intent:
- Make the internal OpenAI usage report default to a `last_24_hours` reporting window when no explicit start/end is provided.
- Include the applied reporting window in the response range metadata.
- Add session-cost sort parameters for `requests_by_session` so the Mission Control UI can drive clickable sortable columns.
- Support sorting by timestamp/newest-oldest, session id, vertical, model, request count, token totals, latency, missing-token count, estimated spend, and generated-name count.
- Keep the existing endpoint and payload fields backward-compatible; do not change unrelated Mission Control reporting behavior.

Expected Mission Control effect:
- The Estimated cost by session table can default to the last 24 hours.
- The UI can make session table columns clickable by passing `session_sort` and `session_sort_direction`.
- Newest-to-oldest sorting is available via the default `timestamp` descending sort.

Validation run:
- `python -m py_compile app.py namengine/core/mission_control_telemetry.py`
- `python -m pytest tests/test_mission_control_telemetry_v1.py tests/test_phase21_engine_audit.py -q`
- `git diff --check -- app.py namengine/core/mission_control_telemetry.py tests/test_mission_control_telemetry_v1.py`

Not included:
- Frontend Mission Control dashboard UI changes; the dashboard source was not present in the active NamEngine workspace.
- Changes to unrelated aggregate tables or customer-facing NamEngine pages.

## Feelings Scale premium strength-meter prototype

Status: local review prototype / included in deploy bucket for decision tracking
Branch: current working tree / next local-first release batch

Included intent:
- Explore a more premium mobile Feelings Scale direction without changing production Baby, Pet, or Business pages.
- Create standalone functional local HTML prototypes under `audit_outputs/20260803-feelings-scale-premium-prototype/`.
- Latest preferred prototype uses independent tapered strength meters instead of the previous draggable graph.
- Remove the building graphic and extra explanatory wording from the prototype.
- Make each scale independently slidable, with the meter thinner on the left and thicker on the right.

Review artifact:
- `audit_outputs/20260803-feelings-scale-premium-prototype/business-feelings-strength-meter-prototype.html`
- `audit_outputs/20260803-feelings-scale-premium-prototype/business-feelings-strength-meter-prototype-mobile.png`

Validation run:
- Playwright opened the local HTML, adjusted all three sliders, captured the mobile screenshot, and verified no `.building` element exists.

Not included:
- Production implementation in Baby, Pet, or Business templates/CSS/JS.
- Route changes, results-generation changes, or deployment-ready UI replacement.
- Removal of the older graph prototype file; it remains as comparison-only audit output.

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
- Block free visitors from changing intake/direction to generate a second first-round list in the same vertical/browser session.
- Remove free-result edit links and Feelings Scale adjustment links that could steer users back into regeneration controls.
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
- `python -m py_compile app.py`
- `python -m pytest tests/test_phase7_refinement.py tests/test_phase26_paid_beta_trust_wrapper.py tests/test_results_mobile_stabilization_v1.py -q`
- `git diff --check -- app.py templates/results.html tests/test_phase26_paid_beta_trust_wrapper.py`

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

## Signal Convergence progress graphic

Status: validated locally / included in next push
Branch: current working tree / next local-first release batch

Included intent:
- Replace the generic non-pet progress orbit graphic with a Signal Convergence treatment.
- Show six outer signal orbs converging into the center, pulsing/rippling, then bouncing back out.
- Remove the visible bottom progress-step/bulleted line from the overlay while preserving existing hidden progress behavior.
- Keep Pet's separate Sound check visual untouched.

Expected customer-facing effect:
- The progress moment reads as scattered taste signals coming together into a stronger fit.
- The overlay feels more premium and less like a static stock graphic.
- The panel stays clean without an extra bottom status/bullet line.

Validation run:
- `python -m pytest tests/test_phase14_progress_experience.py -q`
- `git diff --check`
- Local screenshot regenerated at `audit_outputs/20260801-signal-convergence/signal-convergence-progress-panel.png`

Not included:
- Pet Sound check visual redesign.
- Generated screenshot/temp audit artifacts.

## Full Report underline/focus polish

Status: pushed in `c632843` / already on main
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

## Engine audit auth + results contract cleanup

Status: validated locally / held for next combined deploy
Branch: current working tree / next local-first release batch

Included intent:
- Protect enabled `/dev/engine-audit` and `/dev/taste-evolution/<session_id>` routes with the existing Mission Control bearer-token authorization path.
- Keep the audit feature flag behavior intact: flag off returns 404; flag on requires bearer auth.
- Add the trailing-slash `/dev/engine-audit/` route variant for consistency.
- Restore Baby results saved-progress contract/copy after the broad gate found the missing `baby-saved-progress` block.
- Show refinement gate errors inside the completion-state panel so short/completed lists still explain why refinement is blocked.
- Keep Business chosen pages on the deterministic clear brand-card path and include the clear-card label contract.

Expected effect:
- Internal audit routes are not exposed merely by turning on `NAMENGINE_ENABLE_ENGINE_AUDIT=1`.
- Baby/Pet/Business result and chosen-page contracts match the current tests and user-facing flows.
- The previous broad-gate failures are cleared without pushing or deploying.

Validation run:
- `python -m pytest --ignore=temp -q`
- Result: `507 passed, 300 subtests passed in 46.10s`

Not included:
- Push/deploy.
- Mission Control frontend changes.
- Cleanup of pre-existing untracked audit/tmp artifacts.
