const { chromium } = require('playwright');

(async () => {
  const br = await chromium.launch();
  // Fresh context = no cookies = unauthenticated (what iMessage crawler sees)
  const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } });
  const pg = await ctx.newPage();

  await pg.goto('http://127.0.0.1:5000/share/baby-7aaca470e7fa', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await pg.waitForTimeout(600);
  console.log('landed:', pg.url());

  // Grab OG tags
  const ogImage = await pg.$eval('meta[property="og:image"]', el => el.content).catch(() => 'MISSING');
  const ogTitle = await pg.$eval('meta[property="og:title"]', el => el.content).catch(() => 'MISSING');
  console.log('og:title =', ogTitle);
  console.log('og:image =', ogImage);

  await pg.screenshot({ path: 'qa-artifacts/paywall-hero-fix/share-page-no-auth.png', fullPage: false });
  await br.close();
})();
