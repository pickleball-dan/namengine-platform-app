const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();

  // Full page — mobile
  const mob = await browser.newPage();
  await mob.setViewportSize({ width: 390, height: 844 });
  await mob.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await mob.waitForTimeout(700);
  await mob.screenshot({ path: 'tmp_full_mobile.png', fullPage: true });

  // Full page — desktop
  const desk = await browser.newPage();
  await desk.setViewportSize({ width: 1440, height: 900 });
  await desk.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await desk.waitForTimeout(700);
  await desk.screenshot({ path: 'tmp_full_desktop.png', fullPage: true });

  await browser.close();
  console.log('done');
})();
