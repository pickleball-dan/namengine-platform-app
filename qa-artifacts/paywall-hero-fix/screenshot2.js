const { chromium } = require('playwright');

(async () => {
  const br = await chromium.launch();
  const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } });

  // Screenshot the results session (no paywall redirect)
  const p1 = await ctx.newPage();
  await p1.goto('http://127.0.0.1:5000/results/session/business-5ed36fba35d8', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await p1.waitForTimeout(800);
  await p1.screenshot({ path: 'qa-artifacts/paywall-hero-fix/03-results-no-paywall.png', fullPage: false });
  console.log('03-results done, url:', p1.url());
  await p1.close();

  // Also get the access/hero page again for comparison
  const p2 = await ctx.newPage();
  await p2.goto('http://127.0.0.1:5000/business/access', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await p2.waitForTimeout(600);
  await p2.screenshot({ path: 'qa-artifacts/paywall-hero-fix/01-access-hero-final.png', fullPage: false });
  console.log('01-access-hero done');
  await p2.close();

  await br.close();
})();
