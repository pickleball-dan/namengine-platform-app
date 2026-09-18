const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();

  // Mobile — primary target
  const mob = await browser.newPage();
  await mob.setViewportSize({ width: 390, height: 844 });
  await mob.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await mob.waitForTimeout(700);

  // Hero with new CTA
  await mob.screenshot({ path: 'tmp_conv_hero_mobile.png' });

  // Learning loop now right after vertical cards
  await mob.evaluate(() => document.querySelector('.landing-loop-section').scrollIntoView({ block: 'center' }));
  await mob.waitForTimeout(400);
  await mob.screenshot({ path: 'tmp_conv_loop_mobile.png' });

  // Desktop hero
  const desk = await browser.newPage();
  await desk.setViewportSize({ width: 1440, height: 900 });
  await desk.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await desk.waitForTimeout(700);
  await desk.screenshot({ path: 'tmp_conv_hero_desktop.png' });

  await browser.close();
  console.log('done');
})();
