const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'tmp_landing_fullpage.png', fullPage: true });
  await browser.close();
  console.log('done');
})();
