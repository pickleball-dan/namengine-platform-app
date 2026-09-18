const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await page.waitForTimeout(600);

  // Force show each hover card via CSS injection, scroll to section
  const cards = ['baby', 'pet', 'business'];
  for (const v of cards) {
    await page.evaluate((vertical) => {
      document.querySelectorAll('style[data-vc]').forEach(s => s.remove());
      const s = document.createElement('style');
      s.dataset.vc = '1';
      s.textContent = `.landing-vertical-card.${vertical} .vc-hover { opacity: 1 !important; transform: translateY(0) !important; pointer-events: auto !important; }`;
      document.head.appendChild(s);
      document.querySelector('.landing-vertical-card.' + vertical).scrollIntoView({ block: 'center' });
    }, v);
    await page.waitForTimeout(350);
    await page.screenshot({ path: `tmp_desktop_hover_${v}.png` });
  }

  // All three cards visible together with baby hovered
  await page.evaluate(() => {
    document.querySelectorAll('style[data-vc]').forEach(s => s.remove());
    const s = document.createElement('style');
    s.dataset.vc = '1';
    s.textContent = `.landing-vertical-card.baby .vc-hover { opacity: 1 !important; transform: translateY(0) !important; pointer-events: auto !important; }`;
    document.head.appendChild(s);
    document.getElementById('naming-experiences').scrollIntoView({ block: 'start' });
  });
  await page.waitForTimeout(350);
  await page.screenshot({ path: 'tmp_desktop_hover_all3.png' });

  await browser.close();
  console.log('done');
})();
