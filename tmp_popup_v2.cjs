const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 390, height: 844 });

  // Baby pill (hero)
  await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
  await page.click('.landing-pill[data-vertical="baby"]');
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'tmp_v2_baby_pill.png' });

  // Pet pill (hero)
  await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
  await page.click('.landing-pill[data-vertical="pet"]');
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'tmp_v2_pet_pill.png' });

  // Business pill (hero)
  await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
  await page.click('.landing-pill[data-vertical="business"]');
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'tmp_v2_business_pill.png' });

  // Baby vertical card (mid-page section)
  await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
  await page.click('.landing-vertical-card.baby');
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'tmp_v2_baby_card.png' });

  await browser.close();
  console.log('done');
})();
