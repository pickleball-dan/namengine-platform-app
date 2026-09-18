const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();

  // Desktop hero
  const desk = await browser.newPage();
  await desk.setViewportSize({ width: 1440, height: 900 });
  await desk.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await desk.waitForTimeout(700);
  await desk.screenshot({ path: 'tmp_hero_desktop.png' });

  // Vertical cards section desktop
  await desk.evaluate(() => document.getElementById('naming-experiences').scrollIntoView({ block: 'center' }));
  await desk.waitForTimeout(400);
  await desk.screenshot({ path: 'tmp_cards_desktop.png' });

  // Mobile hero
  const mob = await browser.newPage();
  await mob.setViewportSize({ width: 390, height: 844 });
  await mob.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await mob.waitForTimeout(600);
  await mob.screenshot({ path: 'tmp_hero_mobile.png' });

  await browser.close();
  console.log('done');
})();
