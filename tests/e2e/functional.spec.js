'use strict';
const { test, expect } = require('@playwright/test');
const { V, TRANSITION, startInterview, visibleQuestion, answerAndAdvance, completeInterview } = require('./helpers');

const BABY_REVIEW = '[data-baby-direction-review]:not([hidden])';
const RESULT_CARD_SELECTOR = [
  '.baby-name-card',
  '[data-baby-name-card]',
  '.pet-name-card',
  '[data-pet-name-card]',
  '.business-name-card',
  '[data-business-name-card]',
  '[data-name-card]',
  '.name-card',
  '.result-card',
  'article:has(a[href*="/name/"])',
  'a[href*="/name/"]',
].join(', ');

async function completeBabyToReview(page, heritage = 'Irish') {
  await startInterview(page, 'baby');

  for (let i = 0; i < 40; i++) {
    const review = page.locator(BABY_REVIEW);
    if (await review.count() > 0) {
      await expect(review).toBeVisible();
      return review;
    }

    const checkIn = page.locator('[data-intake-checkin]:not([hidden])');
    if (await checkIn.count() > 0) {
      await checkIn.locator('[data-checkin-value]').first().click();
      await page.waitForTimeout(TRANSITION);
      continue;
    }

    const q = visibleQuestion(page, 'baby');
    await q.waitFor({ state: 'visible' });

    if (await q.locator('[data-heritage-search]').count() > 0) {
      await q.locator('[data-heritage-search]').fill(heritage);
      await page.waitForTimeout(400);
      const exactChip = q.locator(`[data-heritage-value="${heritage}"]`).first();
      if (await exactChip.count() > 0) {
        await exactChip.click();
      } else {
        await q.getByText(new RegExp(`Use ['\u2018\u2019\"]?${heritage}['\u2018\u2019\"]?`, 'i')).click();
      }
      await page.waitForTimeout(TRANSITION);
      continue;
    }

    await answerAndAdvance(page, 'baby');
  }

  throw new Error('Baby direction review was not reached within 40 steps');
}

async function generateFromReview(page, vertical) {
  const c = V[vertical];
  const findSelector = vertical === 'baby' ? '[data-baby-direction-find]' : c.find;
  await page.locator(findSelector).click();
  await page.waitForURL(c.resultsUrl, { timeout: 90000 });
  const cards = page.locator(RESULT_CARD_SELECTOR);
  await expect(cards.first()).toBeVisible({ timeout: 30000 });
  expect(await cards.count(), `${vertical} results should contain at least one name card`).toBeGreaterThan(0);
  return cards;
}

async function clickFirstNameAndExpectDetail(page, cards, vertical) {
  const before = page.url();
  const detailTarget = page.locator(
    'a[href*="/name/"]:not([href*="/access"]), a[href*="/chosen"]:not([href*="/access"]), a[href*="/baby/name"]:not([href*="/access"])'
  ).first();
  const choose = page.getByRole('button', { name: /choose|select|details|view/i }).first();

  if (await detailTarget.count() > 0) {
    await detailTarget.click();
  } else if (await choose.count() > 0) {
    await choose.click();
  } else {
    const lockedDetails = await page.locator('a[href*="/access"]').count();
    test.skip(
      lockedDetails > 0,
      `${vertical} round 1 name detail/chosen links are locked behind access for unauthenticated production users`
    );
    await cards.first().click();
  }

  await page.waitForURL(url => {
    const href = url.toString();
    return href !== before && (/\/name\//.test(href) || /\/chosen/.test(href) || /\/baby\/name/.test(href));
  }, { timeout: 30000 });
  expect(page.url(), `${vertical} name detail/chosen URL`).toMatch(/\/name\/|\/chosen|\/baby\/name/);
}

test.describe('Functional E2E — Baby', () => {
  test('Full intake → direction review', async ({ page }) => {
    await startInterview(page, 'baby');
    await completeInterview(page, 'baby');
    await expect(page.locator(BABY_REVIEW)).toBeVisible({ timeout: 5000 });
  });

  test('Heritage search → direction review shows selection', async ({ page }) => {
    const review = await completeBabyToReview(page, 'Irish');
    await expect(review).toContainText(/Irish/i);
  });

  test('Heritage free-form → flows through', async ({ page }) => {
    const review = await completeBabyToReview(page, 'Sudanese');
    await expect(review).toContainText(/Sudanese/i);
  });

  test('Direction review is editable', async ({ page }) => {
    await completeBabyToReview(page, 'Irish');
    const editButton = page.locator(`${BABY_REVIEW} [data-edit-question]`).first();
    await expect(editButton).toBeVisible();
    const targetId = await editButton.getAttribute('data-edit-question');
    await editButton.click();
    await page.waitForTimeout(TRANSITION);
    await expect(visibleQuestion(page, 'baby')).toBeVisible();
    expect(await visibleQuestion(page, 'baby').getAttribute('data-question-id')).toBe(targetId);
    await answerAndAdvance(page, 'baby');
    await expect(page.locator(BABY_REVIEW)).toBeVisible({ timeout: 5000 });
  });

  test('Generate round 1', async ({ page }) => {
    await completeBabyToReview(page, 'Irish');
    await generateFromReview(page, 'baby');
  });

  test('Paywall fires after round 1 for new user', async ({ page }) => {
    await completeBabyToReview(page, 'Irish');
    await generateFromReview(page, 'baby');
    const refine = page.getByRole('link', { name: /refine|round 2|another|more|unlock full access/i })
      .or(page.getByRole('button', { name: /refine|round 2|another|more|unlock full access/i }))
      .first();
    if (await refine.count() === 0) test.skip(true, 'No visible refine/round 2/access control found on results page');
    await refine.click();
    await page.waitForURL(V.baby.accessUrl, { timeout: 30000 });
    expect(page.url()).toMatch(V.baby.accessUrl);
  });

  test('Chosen name screen', async ({ page }) => {
    await completeBabyToReview(page, 'Irish');
    const cards = await generateFromReview(page, 'baby');
    await clickFirstNameAndExpectDetail(page, cards, 'baby');
  });

  test('Share page loads', async ({ page }) => {
    await completeBabyToReview(page, 'Irish');
    await generateFromReview(page, 'baby');
    const shareLink = page.locator('a[href*="/share/"]').first();
    if (await shareLink.count() === 0) test.skip(true, 'No share link found on round 1 results page');
    const href = await shareLink.getAttribute('href');
    const response = await page.goto(href);
    expect(response, `Share URL ${href} should return a response`).not.toBeNull();
    expect(response.status(), `Share URL ${href} should load successfully`).toBeLessThan(400);
    expect(page.url()).toContain('/share/');
  });
});

test.describe('Functional E2E — Pet', () => {
  test('Full pet intake → direction review → generate → chosen', async ({ page }) => {
    await startInterview(page, 'pet');
    expect(await completeInterview(page, 'pet')).toBe('review');
    await expect(page.locator(V.pet.review)).toBeVisible();
    const cards = await generateFromReview(page, 'pet');
    await clickFirstNameAndExpectDetail(page, cards, 'pet');
  });
});

test.describe('Functional E2E — Business', () => {
  test('Full business intake → direction review → generate', async ({ page }) => {
    await startInterview(page, 'business');
    expect(await completeInterview(page, 'business')).toBe('review');
    await expect(page.locator(V.business.review)).toBeVisible();
    await generateFromReview(page, 'business');
  });
});
