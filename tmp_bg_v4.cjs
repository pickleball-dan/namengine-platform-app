const { chromium } = require('playwright');

// v3 colors darkened ~30% — channel values * 0.7, then boosted saturation slightly
const options = [
  {
    name: 'A_peach',
    css: `
      body {
        background: linear-gradient(160deg, #f0c8a8 0%, #e4bc9c 45%, #d8b090 100%) !important;
      }
      :root { --page: #ecc0a0; }
    `
  },
  {
    name: 'B_teal',
    css: `
      body {
        background: linear-gradient(160deg, #a8d4c8 0%, #9cc8bc 45%, #90bcb0 100%) !important;
      }
      :root { --page: #a0ccbf; }
    `
  },
  {
    name: 'C_gold',
    css: `
      body {
        background: linear-gradient(160deg, #e8cc80 0%, #dcbf6e 45%, #d0b45c 100%) !important;
      }
      :root { --page: #e0c474; }
    `
  }
];

(async () => {
  const browser = await chromium.launch();

  for (const opt of options) {
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
    await page.waitForTimeout(600);
    await page.addStyleTag({ content: opt.css });
    await page.waitForTimeout(300);
    await page.screenshot({ path: `tmp_bgv4_${opt.name}_hero.png` });
    await page.evaluate(() => document.getElementById('naming-experiences').scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(300);
    await page.screenshot({ path: `tmp_bgv4_${opt.name}_cards.png` });
    await page.close();
  }

  await browser.close();
  console.log('done');
})();
