'use strict';
const { test, expect } = require('@playwright/test');
const { V, startInterview, visibleQuestion, answerAndAdvance, completeInterview, getCardSizing } = require('./helpers');

// ─── Standing rule: "Skip" must NEVER appear anywhere in Baby's interview ───
// The [data-baby-skip] button must always say "Next", never "Skip".
// This test will FAIL on production until the fix ships — that is intentional.

test.describe('Baby — Skip must never appear', () => {
  test('No visible "Skip" text at any point during the interview', async ({ page }) => {
    await startInterview(page, 'baby');

    for (let step = 0; step < 15; step++) {
      // Check the data-baby-skip button specifically
      const skipBtn = page.locator(`${V.baby.q}:not([hidden]) ${V.baby.skipNext}`);
      if (await skipBtn.count() > 0) {
        const label = (await skipBtn.textContent())?.trim();
        expect(
          label,
          `Step ${step + 1}: [data-baby-skip] reads "${label}" — must never say "Skip"`
        ).not.toBe('Skip');
      }

      // Check no visible element anywhere on the page says exactly "Skip"
      await expect(
        page.getByText('Skip', { exact: true }),
        `Step ${step + 1}: found a visible element with text "Skip"`
      ).toBeHidden();

      if (await page.locator(V.baby.complete).isVisible()) break;
      if (await page.locator(`${V.baby.q}:not([hidden])`).count() === 0) break;
      await answerAndAdvance(page, 'baby');
    }
  });
});

// ─── Baby — Card sizing (Baby IS the standard) ──────────────────────────────
// Desktop: max-width 760px, centered (margin auto).
// Mobile:  card fills viewport — width >= 350px.
// These values are the reference. Pet and Business must match.

// Baby IS the sizing standard — we verify it renders at a sane desktop width
// (>= 600px, <= viewport) and does not overflow at mobile.
// Pet and Business read Baby's computed width dynamically and must match it.
test.describe('Baby — Card sizing (the standard)', () => {
  test('Question card fills at least 65% of viewport — desktop', async ({ page }) => {
    const vp = page.viewportSize();
    if (vp.width < 1024) test.skip();

    await startInterview(page, 'baby');
    const sizing = await getCardSizing(page, V.baby.cardSel);
    expect(sizing, 'Could not read Baby question card sizing').not.toBeNull();

    // Standard: card must fill at least 65% of viewport. Baby defines this standard.
    // Pet and Business must meet the same threshold.
    expect(
      sizing.width,
      `Baby card width is ${sizing.width}px — must be >= 65% of ${vp.width}px viewport (${Math.round(vp.width * 0.65)}px)`
    ).toBeGreaterThanOrEqual(vp.width * 0.65);
  });

  test('Question card fills mobile viewport — no artificial constraint', async ({ page }) => {
    const vp = page.viewportSize();
    if (vp.width >= 1024) test.skip();

    await startInterview(page, 'baby');
    const sizing = await getCardSizing(page, V.baby.cardSel);
    expect(sizing, 'Could not read Baby question card sizing').not.toBeNull();

    expect(
      sizing.width,
      `Baby card width at mobile is ${sizing.width}px — expected >= 350px`
    ).toBeGreaterThanOrEqual(350);
  });
});

// ─── Baby interview flow ─────────────────────────────────────────────────────

test.describe('Baby — Interview flow', () => {
  test.beforeEach(async ({ page }) => {
    await startInterview(page, 'baby');
  });

  test('Exactly one question is visible at a time after Begin', async ({ page }) => {
    await expect(page.locator(`${V.baby.q}:not([hidden])`)).toHaveCount(1);
  });

  test('Back returns to the previous question', async ({ page }) => {
    const q1Id = await visibleQuestion(page, 'baby').getAttribute('data-question-id');

    await answerAndAdvance(page, 'baby');

    const q2Id = await visibleQuestion(page, 'baby').getAttribute('data-question-id');
    expect(q2Id).not.toBe(q1Id);

    await page.locator(V.baby.back).click();
    await page.waitForTimeout(300);

    expect(
      await visibleQuestion(page, 'baby').getAttribute('data-question-id')
    ).toBe(q1Id);
  });

  test('Interview shows completion screen', async ({ page }) => {
    // UI/UX check only — does the completion panel appear after all questions?
    // Name generation is tested elsewhere.
    await completeInterview(page, 'baby');
    await expect(page.locator(V.baby.complete)).toBeVisible({ timeout: 5000 });
  });
});


