const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.waitForTimeout(600);

  // Inject CSS to force-show the baby hover card, then screenshot
  await page.evaluate(() => {
    const style = document.createElement('style');
    style.textContent = '.landing-vertical-card.baby .vc-hover { opacity: 1 !important; transform: translateY(0) !important; pointer-events: auto !important; }';
    document.head.appendChild(style);
    document.querySelector('.landing-vertical-card.baby').scrollIntoView({ block: 'center' });
  });
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp_hover_baby.png' });

  // Pet
  await page.evaluate(() => {
    document.querySelectorAll('style').forEach(s => { if (s.textContent.includes('vc-hover')) s.remove(); });
    const style = document.createElement('style');
    style.textContent = '.landing-vertical-card.pet .vc-hover { opacity: 1 !important; transform: translateY(0) !important; pointer-events: auto !important; }';
    document.head.appendChild(style);
    document.querySelector('.landing-vertical-card.pet').scrollIntoView({ block: 'center' });
  });
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp_hover_pet.png' });

  // Business
  await page.evaluate(() => {
    document.querySelectorAll('style').forEach(s => { if (s.textContent.includes('vc-hover')) s.remove(); });
    const style = document.createElement('style');
    style.textContent = '.landing-vertical-card.business .vc-hover { opacity: 1 !important; transform: translateY(0) !important; pointer-events: auto !important; }';
    document.head.appendChild(style);
    document.querySelector('.landing-vertical-card.business').scrollIntoView({ block: 'center' });
  });
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp_hover_business.png' });

  await browser.close();
  console.log('done');
})();
