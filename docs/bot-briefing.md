# NamEngine — Constraints for automated changes

> **This is a living document.** It is updated by SirDan/Claude each time a new finding in `namengine-turbo-tuning.md` is resolved, reclassified, or reversed. Always use the latest version — check the "Last updated" line below before relying on this for a task. If something here seems out of date relative to the actual codebase, flag it rather than assuming either is correct.

**Last updated:** 2026-08-18 — corrected a stale item (the 3 remaining `/dev/*` routes were fixed on 2026-08-18, this doc still said they were public), added CSRF protection and the Render-proxy secure-cookie fix as "keep" items, and added the "Testing and verification" section drafted on 2026-08-13 that was never actually pushed to this file until now.

Read this before touching any of the areas below. These reflect decisions already made and verified as of the date above. Do not reverse them without flagging the conflict to SirDan first.

## Do not change

1. **`/dev/eval-report` must default to fallback mode.**
	`use_ai = request.args.get("ai") == "1"` in `app.py`. Do not flip this to default `True`/AI-mode. Running all 23 fixtures through the real 3-pass engine synchronously in one request risks exceeding the gunicorn worker timeout and costs real OpenAI spend on every page load. AI mode must stay opt-in via `?ai=1`.

2. **`/dev/eval-report` must require the telemetry bearer token.**
	Route must call `_mission_control_authorized(request.headers.get("Authorization", ""))` and 404 if it fails, same as the other `/dev/*` routes. This route was previously unauthenticated and reachable by anyone; do not remove or weaken this check.

3. **Paid-access token secret must not fall back to `NAMENGINE_TELEMETRY_TOKEN`.**
	`_beta_access_secret()` in `app.py` should only check `NAMENGINE_ACCESS_TOKEN_SECRET`, then fall through to the safe random per-process secret. Do not reintroduce `NAMENGINE_TELEMETRY_TOKEN` as a fallback — it lets the internal telemetry credential also forge customer paywall-bypass tokens.

4. **`/choose`, `/refine`, and `/api/react` must verify a CSRF token before acting.**
	Each checks `_valid_csrf_token(...)` (form field or JSON `csrf_token` for the API route) against the `namengine_csrf` cookie before doing anything else, rejecting with 403 on mismatch. Do not remove or weaken this — without it, a malicious page can forge requests using a visitor's own session (burn a paid refinement round, hijack a chosen name, or pollute reactions) without their consent. If you add new state-changing POST/PUT/DELETE routes, they should get the same check, not just these three.

5. **The 3 previously-public `/dev/*` routes (`engine_audit_index`, `engine_audit`, `taste_evolution`) must keep their bearer-token check.**
	Each calls `_require_engine_audit_authorized()` (401 if the `Authorization: Bearer` header is missing/empty, 403 if the token is wrong) in addition to the existing `_engine_audit_enabled()` flag check. This closed a real gap — these routes were unauthenticated and publicly reachable for a period. Do not remove.

## Keep these (already fixed, working as intended)

- SQLite `PRAGMA journal_mode = WAL` in `namengine/core/storage.py` — keep.
- Configurable OpenAI retries (`NAMENGINE_OPENAI_MAX_RETRIES`, default 1) in `namengine/core/ai_generation.py` — keep.
- Baby vertical now returns `rejected_candidates` on par with other verticals — keep.
- Taste profile now captures `liked_territories` / `disliked_territories` / rationales, not just letter-frequency sound signal — keep.
- `ProxyFix` middleware (`app.wsgi_app = ProxyFix(...)` in `create_app()`) — keep. Without this, `request.is_secure` doesn't correctly reflect the real client connection behind Render's reverse proxy, which would silently break every `secure=request.is_secure` cookie in the app (visitor cookie, beta-access cookie, CSRF cookie) in production.

## Flag before acting, don't decide unilaterally

- **`gunicorn.conf.py` / `Procfile` / `render.yaml` timeout is currently 420s** (raised from 240s specifically to accommodate the AI-default eval-report change, which has since been reverted). Whether it should go back to 240s or stay at 420s is still an open question as of this update — confirmed still 420s, nobody has decided either way. Ask before changing in either direction.
- **Any change to per-vertical copy/template logic** (`results.html`, `intake.html`, and ~8 other templates with hardcoded `vertical.slug ==` branches, plus the local Jinja dicts `result_framing`/`saved_notes`/`result_cta_labels`/`flow_copy`/`textarea_tooltips`). This is a known architectural drift risk being tracked, not yet restructured — don't refactor without confirming approach first.
- **Business vertical's no-fallback-on-AI-failure behavior** (`fallback_on_provider_error=vertical.slug != "business"` in `app.py`) is intentional per a locked-in test (`test_business_provider_failure_still_does_not_fallback_or_record_successful_fallback`). Don't "fix" this without confirming — it's a deliberate quality-bar decision, not a bug.

## Testing and verification

1. **Use `pytest`, not `python -m unittest discover`, to run the test suite.**
	`tests/conftest.py` has an `autouse` fixture (`_disable_live_openai_by_default`) that blanks `OPENAI_API_KEY` for every test unless `NAMENGINE_ALLOW_LIVE_OPENAI_IN_TESTS=1` is explicitly set. This fixture is pytest-specific and does **not** run under `unittest discover` — meaning a full suite run via `unittest discover` can silently make real, slow OpenAI calls that `pytest` would have blocked by default. This caused unexplained multi-minute hangs and failure-count mismatches between environments earlier in this project. Correct invocation:
	```
	pytest
	```
	or, to target one file:
	```
	pytest tests/test_some_file.py -v
	```
	Do not use `python -m unittest discover -s tests -p "test_*.py"` for full-suite validation going forward.

2. **Never report a test result without pasting the actual command output.** A summary statement ("tests pass," "already fixed") is not sufficient — paste the literal terminal output, including the final `Ran N tests...` / `X passed, Y failed` line and any `FAIL:`/`ERROR:` lines. This project has hit multiple situations where a reported result didn't match the actual code on `main` when independently re-verified.

3. **Before claiming a file already matches an expected state, verify against a clean checkout**, not just the local working copy — uncommitted local changes from an earlier step in the same session can make a file appear already-fixed when the committed version on `main` is not.

4. **Stage only the files you actually changed for a given task.** Do not use `git add -A` or `git add .` for a scoped fix — this working directory has historically accumulated unrelated uncommitted changes and untracked `tmp_*`/`audit_outputs/`/`qa-artifacts/` files across sessions; a broad `git add` risks bundling unreviewed work into an unrelated commit.

## Full context

Complete findings and reasoning: `namengine-turbo-tuning.md` (shared separately). This briefing is the short version — when in doubt, the full doc is the source of truth.

## Changelog

- **2026-08-18** — Corrected item on the 3 `/dev/*` routes (fixed as of `b78ed2d` "Secure audit routes and clean result contracts" — moved from "Flag before acting" to "Do not change"). Added CSRF protection (`6e06c07`) and the `ProxyFix`/secure-cookie fix (`dabc978`) as new entries. Added the "Testing and verification" section, which was drafted during the 2026-08-13 session but never actually committed to this file until now — a real gap worth noting: a drafted update sitting only in conversation isn't a living document, it has to actually be pushed.
- **2026-08-13 (later)** — Added "Testing and verification" section after diagnosing that `unittest discover` bypasses the pytest-only `conftest.py` fixture blocking live OpenAI calls, causing unexplained hangs and failure-count mismatches. Also added standing guidance on pasting actual command output rather than summarizing results, and verifying against a clean checkout before claiming a file is already fixed — both prompted by two separate incidents this session where a reported "already passing" status didn't match what was actually on `main`.
- **2026-08-13** — Initial version. Captures resolved S1 (eval-report auth), S2 (paid-access secret fallback), the reverted eval-report AI-default change, and open architecture/security items still pending.
