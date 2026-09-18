const { chromium } = require('playwright');
const SESSION_ID = 'business-5ed36fba35d8';
const BASE = 'http://127.0.0.1:5001';
const VP = { width: 390, height: 844 };

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: VP });
  const page = await ctx.newPage();

  // ── 1. Access page — email section fix ──────────────────────────────
  await page.goto(`${BASE}/business/access`, { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'ss_01_access_top.png' });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'ss_01b_access_email.png' });
  console.log('1. Access done');

  // ── 2. Intake welcome — hero-action-note ────────────────────────────
  await page.goto(`${BASE}/business/intake`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'ss_02_intake_welcome.png' });
  console.log('2. Intake welcome done');

  // ── 3. Intake — force-show question with optional hint ──────────────
  // Click begin to initialize JS
  try {
    const btn = page.locator('.baby-begin-button').first();
    await btn.click({ timeout: 3000 });
    await page.waitForTimeout(500);
  } catch(e) {}
  // Force-show a question with optional hint text
  const shown = await page.evaluate(() => {
    const hints = [...document.querySelectorAll('.business-optional-hint')];
    for (const h of hints) {
      const q = h.closest('[data-business-question]');
      if (q) {
        document.querySelectorAll('[data-business-question]').forEach(el => el.setAttribute('hidden',''));
        q.removeAttribute('hidden');
        const stage = document.querySelector('.business-question-stage');
        if (stage) stage.removeAttribute('hidden');
        return true;
      }
    }
    return false;
  });
  if (shown) {
    await page.evaluate(() => {
      const q = document.querySelector('[data-business-question]:not([hidden])');
      if (q) q.scrollIntoView({ block: 'start' });
    });
    await page.waitForTimeout(400);
    await page.screenshot({ path: 'ss_03_intake_hint.png' });
    console.log('3. Intake hint done');
  } else {
    console.log('3. No hint question found — skipping');
  }

  // ── 4. Results — set unlock cookie then load results ────────────────
  // Use the dev server's own cookie path for access
  // First hit the access page to establish visitor cookie
  await page.goto(`${BASE}/business/access`, { waitUntil: 'networkidle' });
  // Try navigating directly to results (may work for round 1 free sessions)
  await page.goto(`${BASE}/business/session/${SESSION_ID}`, { waitUntil: 'networkidle' });
  const url = page.url();
  console.log('Results URL:', url);
  if (!url.includes('access')) {
    await page.screenshot({ path: 'ss_04_results_top.png' });
    await page.evaluate(() => window.scrollBy(0, 500));
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'ss_05_results_cards.png' });
    await page.evaluate(() => window.scrollBy(0, 600));
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'ss_06_results_lower.png' });
    console.log('4-6. Results done');
  } else {
    console.log('Results redirected to access page — session is paywalled');
    await page.screenshot({ path: 'ss_04_results_redirect.png' });
  }

  await browser.close();
  console.log('All done');
})();
