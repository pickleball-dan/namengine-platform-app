const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  // iPhone 14 Pro viewport
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.waitForTimeout(600);

  // Scroll to vertical cards, screenshot before tap
  await page.evaluate(() => {
    document.getElementById('naming-experiences').scrollIntoView({ block: 'start' });
  });
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp_mobile_cards_normal.png' });

  // Simulate first tap: add vc-active to baby card
  await page.evaluate(() => {
    document.querySelector('.landing-vertical-card.baby').classList.add('vc-active');
    document.querySelector('.landing-vertical-card.baby .vc-hover').removeAttribute('aria-hidden');
  });
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'tmp_mobile_baby_tapped.png' });

  // Simulate tap on pet card
  await page.evaluate(() => {
    document.querySelectorAll('.landing-vertical-card').forEach(c => c.classList.remove('vc-active'));
    document.querySelector('.landing-vertical-card.pet').classList.add('vc-active');
  });
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'tmp_mobile_pet_tapped.png' });

  await browser.close();
  console.log('done');
})();
