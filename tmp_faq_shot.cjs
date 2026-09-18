const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Desktop — FAQ closed
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.waitForTimeout(600);
  await page.evaluate(() => document.getElementById('faq').scrollIntoView({ block: 'center' }));
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp_faq_desktop_closed.png' });

  // Desktop — one open
  await page.evaluate(() => document.querySelector('.landing-faq-item').setAttribute('open', ''));
  await page.waitForTimeout(200);
  await page.screenshot({ path: 'tmp_faq_desktop_open.png' });

  // Mobile
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    document.getElementById('faq').scrollIntoView({ block: 'start' });
    document.querySelector('.landing-faq-item').setAttribute('open', '');
  });
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'tmp_faq_mobile.png' });

  await browser.close();
  console.log('done');
})();
