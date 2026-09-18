const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.waitForTimeout(600);

  // Show the real home page (no hover)
  await page.screenshot({ path: 'tmp_real_home.png' });

  // Baby hover
  await page.evaluate(() => {
    const s = document.createElement('style');
    s.dataset.vc = '1';
    s.textContent = `.landing-vertical-card.baby .vc-hover { opacity:1!important; transform:translateY(0)!important; pointer-events:auto!important; }`;
    document.head.appendChild(s);
    document.querySelector('.landing-vertical-card.baby').scrollIntoView({ block: 'center' });
  });
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'tmp_real_hover_baby.png' });

  // All 3 visible, baby hovered
  await page.evaluate(() => {
    document.querySelector('#naming-experiences').scrollIntoView({ block: 'start' });
  });
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'tmp_real_hover_all3.png' });

  await browser.close();
  console.log('done');
})();
