# NamEngine Baby Beta RC1 Readiness Report

Date: 2026-07-17

Baseline: `main` at `39e8a1d`

Scope: External Baby beta readiness only; architecture, features, engine design, and taxonomy remained frozen.

## Launch recommendation

**Conditional GO for a limited external parent beta.**

RC1 is suitable for real parent testing after deployment confirms that the OpenAI key/model configuration is present and one production-like Baby generation succeeds. No Critical issues remain. The one High issue found in this pass was fixed and verified on mobile.

## Ranked issues

### Critical

No Critical issues found.

### High

1. **Fixed — Mobile homepage hero collapsed into an unreadable desktop preview column.**
   - At 390×844, the main headline and Baby CTA were pushed far below the fold while the preview panel shrank into a narrow strip.
   - Cause: a later desktop `.home-hero { display: flex; }` rule overrode the earlier responsive grid behavior.
   - Fix: added a final mobile containment override that stacks the hero copy and preview at full width.
   - Regression coverage: `test_mobile_homepage_overrides_late_desktop_flex_hero`.
   - Verification: headline and both CTAs are visible at full width; preview cards stack normally; no horizontal overflow or broken images.

### Medium — post-beta

1. **AI-disabled fallback can miss a selected female heritage lane.**
   - Reproduction: Girl + Italian heritage + Family heritage + classic/soft produced no Italian candidates in fallback mode, even after a refinement prompt requested Italian names.
   - This is not on the configured beta path: the live provider returned Elettra, Livia, Alessia, Serena, Viola, Ginevra, Noemi, and Caterina for the same brief.
   - Recommendation: keep `OPENAI_API_KEY` and the Baby AI-primary configuration as launch requirements. Address fallback heritage/gender coverage after beta because resolving it would continue taxonomy work.

2. **Mobile header navigation touch targets are smaller than ideal.**
   - Header links measured roughly 21–30px high at 390px, although primary flow controls measured 46–54px and worked correctly.
   - Recommendation: increase header-link hit areas in a post-beta accessibility polish pass.

### Low — post-beta

1. **Chosen-name image empty state is implementation-flavored when image creation is not configured.**
   - The page remains usable and clearly shows the chosen name, but displays “Image creation is not configured.”

2. **Homepage includes internal product-system language.**
   - Phrases such as “Shared vertical system” and “Baby paid beta ready” are understandable but less parent-focused than the rest of the Baby experience.

3. **Fixed — `Namegine` brand typo on the homepage.**
   - Corrected two visible instances to `NamEngine`; updated the existing contract test.

## End-to-end verification

Verified at desktop 1440×1000 and mobile 390×844:

- Homepage to Baby intake navigation.
- Required-field validation for gender direction, style, and sound.
- Intake persistence into the Feelings Scale.
- Feelings Scale priority data and progress overlay.
- Clean saved-session results URL after generation.
- Eight-result first round with no broken images or horizontal overflow.
- Love/No reaction persistence, saved-count update, and three-reaction refinement gate.
- Regeneration into Round 2 with eight new names and no first-round repeats.
- Mobile result accordion, including hidden details and a 48px visible Choose action after expansion.
- Name detail, chosen-name completion, compare, and shared-list navigation.
- Clear empty refinement state before three reactions.
- Safe generation-unavailable behavior and stale-session handling through automated coverage.
- Legal/trust navigation and result disclaimer presence.

## Recommendation quality check

- Live provider smoke test completed successfully in 16.9 seconds.
- The selected Italian heritage lane was reflected strongly in all eight live recommendations.
- Offline fallback behavior was also exercised to make reaction/regeneration testing deterministic; its heritage limitation is recorded above rather than expanded into taxonomy work.

## Automated verification

- Full suite: **299 tests passed**.
- Focused mobile regression: **9 tests passed**.
- Browser checks: no horizontal overflow or broken images on the tested homepage, intake, results, compare, and share views.

## Launch conditions

Before inviting parents:

1. Confirm `OPENAI_API_KEY` and the intended `NAMENGINE_OPENAI_MODEL` are configured in the beta environment.
2. Run one deployed Baby generation and confirm a saved-session results URL returns eight names.
3. Confirm generation-failure logging/monitoring is visible to the team without exposing provider details to parents.
