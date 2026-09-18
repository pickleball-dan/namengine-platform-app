const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const br = await chromium.launch();
  const pg = await br.newPage();
  await pg.setViewportSize({ width: 800, height: 500 });
  const file = path.resolve('qa-artifacts/paywall-hero-fix/logo-frame-check.html');
  await pg.goto('file://' + file, { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(400);
  await pg.screenshot({ path: 'qa-artifacts/paywall-hero-fix/logo-frame-before-after.png', fullPage: false });
  console.log('done');
  await br.close();
})();
