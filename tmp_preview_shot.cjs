const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();

  // Desktop
  const desk = await browser.newPage();
  await desk.setViewportSize({ width: 1440, height: 900 });
  await desk.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await desk.waitForTimeout(600);
  await desk.evaluate(() => document.getElementById('what-you-get').scrollIntoView({ block: 'center' }));
  await desk.waitForTimeout(400);
  await desk.screenshot({ path: 'tmp_preview_desktop.png' });

  // Mobile
  const mob = await browser.newPage();
  await mob.setViewportSize({ width: 390, height: 844 });
  await mob.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await mob.waitForTimeout(500);
  await mob.evaluate(() => document.getElementById('what-you-get').scrollIntoView({ block: 'start' }));
  await mob.waitForTimeout(300);
  await mob.screenshot({ path: 'tmp_preview_mobile.png' });

  await browser.close();
  console.log('done');
})();
