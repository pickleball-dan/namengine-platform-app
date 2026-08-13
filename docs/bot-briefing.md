# NamEngine — Constraints for automated changes

> **This is a living document.** It is updated by SirDan/Claude each time a new finding in `namengine-turbo-tuning.md` is resolved, reclassified, or reversed. Always use the latest version — check the "Last updated" line below before relying on this for a task. If something here seems out of date relative to the actual codebase, flag it rather than assuming either is correct.

**Last updated:** 2026-08-13 — after reverting the eval-report AI-default change and confirming provenance (SirDan-directed Openclaw run, not unauthorized access).

Read this before touching any of the areas below. These reflect decisions already made and verified as of the date above. Do not reverse them without flagging the conflict to SirDan first.

## Do not change

1. **`/dev/eval-report` must default to fallback mode.**
	`use_ai = request.args.get("ai") == "1"` in `app.py`. Do not flip this to default `True`/AI-mode. Running all 23 fixtures through the real 3-pass engine synchronously in one request risks exceeding the gunicorn worker timeout and costs real OpenAI spend on every page load. AI mode must stay opt-in via `?ai=1`.

2. **`/dev/eval-report` must require the telemetry bearer token.**
	Route must call `_mission_control_authorized(request.headers.get("Authorization", ""))` and 404 if it fails, same as the other `/dev/*` routes. This route was previously unauthenticated and reachable by anyone; do not remove or weaken this check.

3. **Paid-access token secret must not fall back to `NAMENGINE_TELEMETRY_TOKEN`.**
	`_beta_access_secret()` in `app.py` should only check `NAMENGINE_ACCESS_TOKEN_SECRET`, then fall through to the safe random per-process secret. Do not reintroduce `NAMENGINE_TELEMETRY_TOKEN` as a fallback — it lets the internal telemetry credential also forge customer paywall-bypass tokens.

## Keep these (already fixed, working as intended)

- SQLite `PRAGMA journal_mode = WAL` in `namengine/core/storage.py` — keep.
- Configurable OpenAI retries (`NAMENGINE_OPENAI_MAX_RETRIES`, default 1) in `namengine/core/ai_generation.py` — keep.
- Baby vertical now returns `rejected_candidates` on par with other verticals — keep.
- Taste profile now captures `liked_territories` / `disliked_territories` / rationales, not just letter-frequency sound signal — keep.

## Flag before acting, don't decide unilaterally

- **`gunicorn.conf.py` / `Procfile` / `render.yaml` timeout is currently 420s** (raised from 240s specifically to accommodate the AI-default eval-report change, which has since been reverted). Whether it should go back to 240s or stay at 420s is an open question — ask before changing either direction.
- **Any change to `/dev/*` routes' auth model** — these routes currently rely on `NAMENGINE_ENABLE_ENGINE_AUDIT=1` (permanently on in production) plus, for eval-report only, the bearer token. The other three `/dev/*` routes (`engine_audit_index`, `engine_audit`, `taste_evolution`) still lack the token check and are effectively public. Don't silently fix or silently leave these — ask which is wanted.
- **Any change to per-vertical copy/template logic** (`results.html`, `intake.html`, and ~8 other templates with hardcoded `vertical.slug ==` branches, plus the local Jinja dicts `result_framing`/`saved_notes`/`result_cta_labels`/`flow_copy`/`textarea_tooltips`). This is a known architectural drift risk being tracked, not yet restructured — don't refactor without confirming approach first.
- **Business vertical's no-fallback-on-AI-failure behavior** (`fallback_on_provider_error=vertical.slug != "business"` in `app.py`) is intentional per a locked-in test (`test_business_provider_failure_still_does_not_fallback_or_record_successful_fallback`). Don't "fix" this without confirming — it's a deliberate quality-bar decision, not a bug.

## Full context

Complete findings and reasoning: `namengine-turbo-tuning.md` (shared separately). This briefing is the short version — when in doubt, the full doc is the source of truth.

## Changelog

- **2026-08-13** — Initial version. Captures resolved S1 (eval-report auth), S2 (paid-access secret fallback), the reverted eval-report AI-default change, and open architecture/security items still pending.
