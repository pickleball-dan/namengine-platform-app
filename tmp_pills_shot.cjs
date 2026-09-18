const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();

  // Mobile
  const mob = await browser.newPage();
  await mob.setViewportSize({ width: 390, height: 844 });
  await mob.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await mob.waitForTimeout(700);
  await mob.screenshot({ path: 'tmp_pills_mobile.png' });

  // Desktop
  const desk = await browser.newPage();
  await desk.setViewportSize({ width: 1440, height: 900 });
  await desk.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await desk.waitForTimeout(700);
  await desk.screenshot({ path: 'tmp_pills_desktop.png' });

  await browser.close();
  console.log('done');
})();
