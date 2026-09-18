const { chromium } = require('playwright');

const options = [
  {
    name: 'A_teal',
    css: `
      body {
        background: linear-gradient(160deg, #0e3d35 0%, #1a5c4e 35%, #0f3028 70%, #0a2420 100%) !important;
      }
      .landing-hero {
        background: linear-gradient(135deg, rgba(255,255,255,0.86), rgba(180,225,215,0.25)), #12453d !important;
      }
    `
  },
  {
    name: 'B_warm',
    css: `
      body {
        background: linear-gradient(160deg, #3a1e12 0%, #4e2c18 30%, #2e1a14 65%, #1e1008 100%) !important;
      }
      .landing-hero {
        background: linear-gradient(135deg, rgba(255,255,255,0.88), rgba(255,180,140,0.22)), #3c2018 !important;
      }
    `
  },
  {
    name: 'C_blend',
    css: `
      body {
        background: linear-gradient(160deg, #0e2e38 0%, #183a30 35%, #2c2010 65%, #1a160a 100%) !important;
      }
      .landing-hero {
        background: linear-gradient(135deg, rgba(255,255,255,0.88), rgba(180,215,220,0.22)), #142830 !important;
      }
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
    await page.screenshot({ path: `tmp_bgv2_${opt.name}_hero.png` });
    await page.evaluate(() => document.getElementById('naming-experiences').scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(300);
    await page.screenshot({ path: `tmp_bgv2_${opt.name}_cards.png` });
    await page.close();
  }

  await browser.close();
  console.log('done');
})();
