const { chromium } = require('playwright');

const options = [
  {
    name: 'A_peach',
    css: `
      body {
        background: linear-gradient(160deg, #fdf0e8 0%, #f8e8dc 45%, #f4e0d0 100%) !important;
      }
      :root { --page: #f8eae0; }
    `
  },
  {
    name: 'B_teal',
    css: `
      body {
        background: linear-gradient(160deg, #e8f4f0 0%, #ddeee8 45%, #d4e8e0 100%) !important;
      }
      :root { --page: #deeee8; }
    `
  },
  {
    name: 'C_gold',
    css: `
      body {
        background: linear-gradient(160deg, #fdf4e0 0%, #f8edd4 45%, #f2e4c4 100%) !important;
      }
      :root { --page: #f8edd4; }
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
    await page.screenshot({ path: `tmp_bgv3_${opt.name}_hero.png` });
    await page.evaluate(() => document.getElementById('naming-experiences').scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(300);
    await page.screenshot({ path: `tmp_bgv3_${opt.name}_cards.png` });
    await page.close();
  }

  await browser.close();
  console.log('done');
})();
