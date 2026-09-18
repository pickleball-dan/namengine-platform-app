const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const page = await b.newPage();
  await page.setViewportSize({ width: 390, height: 844 });

  await page.goto('http://localhost:5000/business', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'tmp_sweep_biz_intake.png' });

  // Scroll down to see more of the intake hero
  await page.evaluate(() => window.scrollTo(0, 200));
  await page.screenshot({ path: 'tmp_sweep_biz_intake_scroll.png' });

  await b.close();
  console.log('done');
})();
