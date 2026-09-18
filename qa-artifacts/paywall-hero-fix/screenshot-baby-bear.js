const { chromium } = require('playwright');

(async () => {
  const br = await chromium.launch();
  const ctx = await br.newContext({ viewport: { width: 390, height: 844 } });
  const pg = await ctx.newPage();

  // POST baby intake directly to trigger generation + progress overlay
  await pg.goto('http://127.0.0.1:5000/baby', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await pg.waitForTimeout(500);

  // Inject: force show the progress overlay with baby-thinking-panel and is-searching
  await pg.evaluate(() => {
    const overlay = document.querySelector('[data-progress-overlay]');
    const visual = document.querySelector('[data-progress-visual]');
    const panel = document.querySelector('.progress-panel');
    if (overlay) overlay.removeAttribute('hidden');
    if (visual) {
      visual.classList.add('is-searching');
      // Set phase 3 so bubbles show
      visual.setAttribute('data-progress-phase', '3');
    }
    if (panel) panel.classList.add('baby-thinking-panel');
    document.body.classList.add('vertical-baby');
  });
  await pg.waitForTimeout(800);
  await pg.screenshot({ path: 'qa-artifacts/paywall-hero-fix/baby-bear-local.png', fullPage: false });
  console.log('done');
  await br.close();
})();
