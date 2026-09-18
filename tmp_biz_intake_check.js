const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const page = await b.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://localhost:5000/business', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'tmp_biz_intake_fix.png', fullPage: false });
  await b.close();
  console.log('done');
})();
