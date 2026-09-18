const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();

  // Mobile viewport (primary target)
  const page = await browser.newPage();
  await page.setViewportSize({ width: 390, height: 844 });

  // 1. Full landing page (no popup)
  await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'tmp_landing_full.png' });

  // 2. Baby pill -> popup
  await page.click('.landing-pill[data-vertical="baby"]');
  await page.waitForTimeout(700);
  await page.screenshot({ path: 'tmp_popup_baby.png' });

  // 3. Close / reload, click Pet
  await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
  await page.click('.landing-pill[data-vertical="pet"]');
  await page.waitForTimeout(700);
  await page.screenshot({ path: 'tmp_popup_pet.png' });

  // 4. Close / reload, click Business
  await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
  await page.click('.landing-pill[data-vertical="business"]');
  await page.waitForTimeout(700);
  await page.screenshot({ path: 'tmp_popup_business.png' });

  await browser.close();
  console.log('done');
})();
