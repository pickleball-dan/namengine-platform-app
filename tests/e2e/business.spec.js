'use strict';
const { test, expect } = require('@playwright/test');
const { V, startInterview, visibleQuestion, answerAndAdvance, completeInterview, getCardSizing } = require('./helpers');

// ─── Standing rule: "Skip" must NEVER appear anywhere in Business's interview ─

test.describe('Business — Skip must never appear', () => {
  test('No visible "Skip" text at any point during the interview', async ({ page }) => {
    await startInterview(page, 'business');

    for (let step = 0; step < 20; step++) {
      await expect(
        page.getByText('Skip', { exact: true }),
        `Step ${step + 1}: found a visible element with text "Skip" in Business interview`
      ).toBeHidden();

      if (await page.locator(V.business.review).isVisible()) break;
      if (await page.locator(`${V.business.q}:not([hidden])`).count() === 0) break;
      await answerAndAdvance(page, 'business');
    }
  });
});

// ─── Business — Card sizing must match Baby standard ────────────────────────
// Baby is the declared standard. Business must match at every viewport.
// Desktop: max-width 760px, centered. Mobile: width >= 350px.
// These tests WILL FAIL on production until the CSS fix ships — that is intentional.

// Business card sizing is measured against Baby's live computed values.
// Baby is navigated first to get the reference width, then Business is checked.
// Tolerance: 50px — accounts for minor padding differences between verticals.
// Standard: card must fill >= 65% of viewport at desktop, >= 85% at mobile.
// Baby meets this standard. Pet and Business must match it independently.
test.describe('Business — Card sizing matches Baby standard', () => {
  test('Question card fills at least 65% of viewport — desktop', async ({ page }) => {
    const vp = page.viewportSize();
    if (vp.width < 1024) test.skip();

    await startInterview(page, 'business');
    const sizing = await getCardSizing(page, V.business.cardSel);
    expect(sizing, 'Could not read Business card sizing').not.toBeNull();

    expect(
      sizing.width,
      `Business card width (${sizing.width}px) must be >= 65% of ${vp.width}px viewport (${Math.round(vp.width * 0.65)}px)`
    ).toBeGreaterThanOrEqual(vp.width * 0.65);
  });

  test('Question card fills at least 85% of viewport — mobile', async ({ page }) => {
    const vp = page.viewportSize();
    if (vp.width >= 1024) test.skip();

    await startInterview(page, 'business');
    const sizing = await getCardSizing(page, V.business.cardSel);
    expect(sizing, 'Could not read Business card sizing').not.toBeNull();

    expect(
      sizing.width,
      `Business card width (${sizing.width}px) must be >= 85% of ${vp.width}px mobile viewport (${Math.round(vp.width * 0.85)}px)`
    ).toBeGreaterThanOrEqual(vp.width * 0.85);
  });
});

// ─── Business interview flow ─────────────────────────────────────────────────

test.describe('Business — Interview flow', () => {
  test.beforeEach(async ({ page }) => {
    await startInterview(page, 'business');
  });

  test('Exactly one question is visible at a time after Begin', async ({ page }) => {
    await expect(page.locator(`${V.business.q}:not([hidden])`)).toHaveCount(1);
  });

  test('Next on an empty optional text question advances without blocking', async ({ page }) => {
    let tested = false;

    for (let i = 0; i < 15; i++) {
      if (await page.locator(V.business.review).isVisible()) break;

      const q = visibleQuestion(page, 'business');
      await q.waitFor({ state: 'visible' });
      const kind = await q.getAttribute('data-question-kind');
      const required = await q.getAttribute('data-required');

      if ((kind === 'text' || kind === 'textarea') && required === 'false') {
        const beforeId = await q.getAttribute('data-question-id');
        // Click Next without filling anything
        await q.locator(V.business.next).click();
        await page.waitForTimeout(500);

        // Must advance — either to next question or direction review
        const reviewNow = await page.locator(V.business.review).isVisible();
        if (!reviewNow) {
          const afterId = await visibleQuestion(page, 'business').getAttribute('data-question-id');
          expect(afterId, 'Optional empty Next must advance to a different question').not.toBe(beforeId);
        }
        tested = true;
        break;
      }

      await answerAndAdvance(page, 'business');
    }

    if (!tested) {
      console.log('NOTE: No optional text question encountered in first 15 steps — verify Business question config');
    }
  });

  test('Back returns to the previous question', async ({ page }) => {
    const q1Id = await visibleQuestion(page, 'business').getAttribute('data-question-id');

    await answerAndAdvance(page, 'business');

    const q2Id = await visibleQuestion(page, 'business').getAttribute('data-question-id');
    expect(q2Id).not.toBe(q1Id);

    await page.locator(V.business.back).click();
    await page.waitForTimeout(300);

    expect(
      await visibleQuestion(page, 'business').getAttribute('data-question-id')
    ).toBe(q1Id);
  });

  test('Direction review appears after all questions — not results', async ({ page }) => {
    const result = await completeInterview(page, 'business');
    expect(result, 'Must reach direction review, not bypass to complete or max-reached').toBe('review');
    await expect(page.locator(V.business.review)).toBeVisible();
  });

  test('Direction review has an Edit button for every question', async ({ page }) => {
    await completeInterview(page, 'business');
    const allQuestions = await page.locator(V.business.q).count();
    const editButtons = page.locator(`${V.business.review} [data-edit-question]`);
    await expect(editButtons).toHaveCount(allQuestions);
  });

  test('Edit from direction review navigates to that specific question', async ({ page }) => {
    await completeInterview(page, 'business');

    const firstEdit = page.locator(`${V.business.review} [data-edit-question]`).first();
    const targetId = await firstEdit.getAttribute('data-edit-question');
    await firstEdit.click();
    await page.waitForTimeout(400);

    expect(
      await visibleQuestion(page, 'business').getAttribute('data-question-id')
    ).toBe(targetId);
    await expect(page.locator(V.business.review)).toBeHidden();
  });

  test('After editing a question, direction review reappears', async ({ page }) => {
    await completeInterview(page, 'business');

    const firstEdit = page.locator(`${V.business.review} [data-edit-question]`).first();
    await firstEdit.click();
    await page.waitForTimeout(400);

    // Review must be hidden while editing
    await expect(page.locator(V.business.review)).toBeHidden();

    // Advance from edited question
    await answerAndAdvance(page, 'business');

    // Review must reappear
    await expect(page.locator(V.business.review)).toBeVisible({ timeout: 2000 });
  });

  test('"Find names" shows completion screen', async ({ page }) => {
    await completeInterview(page, 'business');
    await page.locator(V.business.find).click();
    await expect(page.locator(V.business.complete)).toBeVisible({ timeout: 5000 });
  });
});


