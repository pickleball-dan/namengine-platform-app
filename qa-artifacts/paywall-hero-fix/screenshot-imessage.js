const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const br = await chromium.launch();

  // iPhone 14 Pro dimensions
  const ctx = await br.newContext({ viewport: { width: 393, height: 852 } });
  const pg = await ctx.newPage();
  const file = path.resolve('qa-artifacts/paywall-hero-fix/imessage-mock.html');
  await pg.goto('file://' + file, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(500);
  await pg.screenshot({ path: 'qa-artifacts/paywall-hero-fix/imessage-preview.png', fullPage: false });
  console.log('done');
  await br.close();
})();
