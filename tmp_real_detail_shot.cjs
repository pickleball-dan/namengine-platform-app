const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 900, height: 1100 });
  const file = 'file:///' + path.resolve('tmp_real_detail_mock.html').replace(/\\/g, '/');
  await page.goto(file, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: 'tmp_real_detail_shot.png', fullPage: true });
  await browser.close();
  console.log('done');
})();
