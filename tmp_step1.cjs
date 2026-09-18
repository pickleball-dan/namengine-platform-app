const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.waitForTimeout(700);

  // Part A: hero with microcopy
  await page.screenshot({ path: 'tmp_step1_hero.png' });

  // Part B: sample card section
  await page.evaluate(() => {
    document.getElementById('sample-report').scrollIntoView({ block: 'center' });
  });
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp_step1_sample.png' });

  // Mobile view of sample card
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    document.getElementById('sample-report').scrollIntoView({ block: 'start' });
  });
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'tmp_step1_sample_mobile.png' });

  await browser.close();
  console.log('done');
})();
