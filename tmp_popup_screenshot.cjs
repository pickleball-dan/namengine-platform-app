const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();

  // Mobile (iPhone 14)
  const mobile = await browser.newPage();
  await mobile.setViewportSize({ width: 390, height: 844 });
  await mobile.goto('http://localhost:5000', { waitUntil: 'networkidle' });
  await mobile.click('.landing-pill[data-vertical="baby"]');
  await mobile.waitForTimeout(700);
  await mobile.screenshot({ path: 'tmp_popup_mobile.png' });

  // Desktop
  const desktop = await browser.newPage();
  await desktop.setViewportSize({ width: 1280, height: 800 });
  await desktop.goto('http://localhost:5000', { waitUntil: 'networkidle' });
  await desktop.click('.landing-pill[data-vertical="baby"]');
  await desktop.waitForTimeout(700);
  await desktop.screenshot({ path: 'tmp_popup_desktop.png' });

  await browser.close();
  console.log('done');
})();
