const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Desktop — hero
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'tmp_push_hero.png' });

  // Desktop — sample card
  await page.evaluate(() => document.getElementById('sample-report').scrollIntoView({ block: 'center' }));
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp_push_sample_desktop.png' });

  // Mobile — sample card
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.waitForTimeout(500);
  await page.evaluate(() => document.getElementById('sample-report').scrollIntoView({ block: 'start' }));
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'tmp_push_sample_mobile.png' });

  await browser.close();
  console.log('done');
})();
