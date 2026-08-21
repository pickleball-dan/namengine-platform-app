'use strict';

// Shared DOM contracts and utilities for NamEngine E2E tests.
// Each vertical's selectors are defined once here — update here if the DOM changes.

const TRANSITION = 500; // slightly above the 300ms JS animation delay

const V = {
  baby: {
    url:         '/baby',
    q:           '[data-baby-question]',
    // Back is now inside each question — target only the visible one
    back:        '[data-baby-question]:not([hidden]) [data-baby-nav-back]',
    skipNext:    '[data-baby-skip]',       // text questions: shows "Skip" (empty) or "Next" (filled)
    complete:    '[data-baby-complete]',
    bodyClass:   'baby-interview-started',
    hasReview:   false,
    // Production routes to /results/session/baby-{hash} or /baby/(results|feelings)
    resultsUrl:  /\/(results\/session\/baby-|baby\/(results|feelings))/,
    accessUrl:   /\/baby\/access/,
    cardSel:     '.baby-question:not([hidden])',
  },
  pet: {
    url:         '/pet',
    q:           '[data-pet-question]',
    back:        '[data-pet-question]:not([hidden]) [data-pet-nav-back]',
    next:        '[data-pet-next]',
    review:      '[data-pet-direction-review]',
    find:        '[data-pet-direction-find]',
    complete:    '[data-pet-complete]',
    bodyClass:   'pet-interview-started',
    hasReview:   true,
    // Production routes to /results/session/pet-{hash}
    resultsUrl:  /\/(results\/session\/pet-|pet\/(results|feelings))/,
    accessUrl:   /\/pet\/access/,
    cardSel:     '.pet-question:not([hidden])',
  },
  business: {
    url:         '/business',
    q:           '[data-business-question]',
    back:        '[data-business-question]:not([hidden]) [data-business-nav-back]',
    next:        '[data-business-next]',
    review:      '[data-business-direction-review]',
    find:        '[data-business-direction-find]',
    complete:    '[data-business-complete]',
    bodyClass:   'business-interview-started',
    hasReview:   true,
    // Production routes to /results/session/business-{hash}
    resultsUrl:  /\/(results\/session\/business-|business\/results)/,
    accessUrl:   /\/business\/access/,
    cardSel:     '.business-question:not([hidden])',
  },
};

/** Navigate to the vertical's start page and click Begin. */
async function startInterview(page, vertical) {
  const c = V[vertical];
  await page.goto(c.url);
  await page.locator('.baby-begin-button').click();
  await page.waitForFunction(cls => document.body.classList.contains(cls), c.bodyClass);
}

/** Returns a locator for the single currently-visible question. */
function visibleQuestion(page, vertical) {
  return page.locator(`${V[vertical].q}:not([hidden])`);
}

/**
 * Answer the currently visible question with a valid answer and advance.
 *   - Choice / priority: clicks the first non-Other card (auto-advances via change event)
 *   - Text / textarea:   fills with `text`, then clicks Next (or Baby's skipNext button)
 */
async function answerAndAdvance(page, vertical, text = 'E2E test input') {
  const c = V[vertical];
  const q = visibleQuestion(page, vertical);
  await q.waitFor({ state: 'visible' });

  const kind = await q.getAttribute('data-question-kind');

  if (kind === 'choice' || kind === 'priority') {
    const choices = q.locator('[data-choice-value]');
    for (let i = 0; i < await choices.count(); i++) {
      const btn = choices.nth(i);
      if (await btn.getAttribute('data-choice-value') !== 'Other') {
        await btn.click();
        break;
      }
    }
    // Choice auto-advances via change event — wait for transition
    await page.waitForTimeout(TRANSITION);
  } else {
    // Text / textarea
    const textarea = q.locator('textarea').first();
    if (await textarea.count() > 0) {
      await textarea.fill(text);
    } else {
      const input = q.locator(
        'input:not([type="hidden"]):not(.business-native-control):not(.pet-native-control):not([data-other-input])'
      ).first();
      if (await input.count() > 0) await input.fill(text);
    }

    if (vertical === 'baby') {
      await page.locator(`${c.q}:not([hidden]) ${c.skipNext}`).click();
    } else {
      await q.locator(c.next).click();
    }
    await page.waitForTimeout(TRANSITION);
  }
}

/**
 * Walk through ALL questions, answering each one.
 * Returns: 'review' | 'complete' | 'done' | 'max-reached'
 *
 * Baby-specific: handles the mid-interview check-in interstitial
 * ([data-intake-checkin]) which is not a [data-baby-question] element.
 * When the check-in appears, click the first choice and continue.
 */
async function completeInterview(page, vertical) {
  const c = V[vertical];
  const MAX = 40;

  for (let i = 0; i < MAX; i++) {
    if (c.hasReview && await page.locator(c.review).isVisible()) return 'review';
    if (await page.locator(c.complete).isVisible()) return 'complete';

    // Baby: handle the check-in interstitial (not a standard question)
    if (vertical === 'baby') {
      const checkIn = page.locator('[data-intake-checkin]:not([hidden])');
      if (await checkIn.count() > 0) {
        const choice = page.locator('[data-checkin-value]').first();
        if (await choice.count() > 0) {
          await choice.click();
          await page.waitForTimeout(TRANSITION);
          continue;
        }
      }
    }

    const qCount = await page.locator(`${c.q}:not([hidden])`).count();
    if (qCount === 0) return 'done';

    await answerAndAdvance(page, vertical);
  }
  return 'max-reached';
}

/**
 * Read computed sizing for the currently visible question card.
 * Returns { maxWidth (string e.g. '760px'), width (px float),
 *           marginLeft (string), marginRight (string) }
 */
async function getCardSizing(page, cardSelector) {
  return await page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const s = window.getComputedStyle(el);
    return {
      maxWidth:    s.maxWidth,
      width:       parseFloat(s.width),
      marginLeft:  s.marginLeft,
      marginRight: s.marginRight,
    };
  }, cardSelector);
}

module.exports = { V, TRANSITION, startInterview, visibleQuestion, answerAndAdvance, completeInterview, getCardSizing };
