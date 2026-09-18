const { chromium } = require('playwright');

const options = [
  {
    name: 'A_mild',
    label: 'Option A — Mild',
    css: `
      body { background: linear-gradient(160deg, #e4dfd6 0%, #d9d3c8 60%, #cfc8bc 100%) !important; }
      :root { --page: #ddd8ce; --landing-bg: #ddd8ce; }
      .landing-hero { background: linear-gradient(135deg, rgba(255,255,255,0.82), rgba(232,228,220,0.68)), #ddd8ce !important; }
    `
  },
  {
    name: 'B_medium',
    label: 'Option B — Medium',
    css: `
      body { background: linear-gradient(160deg, #cdc6ba 0%, #c2bbb0 60%, #b6afa4 100%) !important; }
      :root { --page: #c8c1b6; --landing-bg: #c8c1b6; }
      .landing-hero { background: linear-gradient(135deg, rgba(255,255,255,0.84), rgba(210,204,194,0.7)), #c8c1b6 !important; }
    `
  },
  {
    name: 'C_deep',
    label: 'Option C — Deep',
    css: `
      body { background: linear-gradient(160deg, #b0a89c 0%, #a49c90 60%, #988f83 100%) !important; }
      :root { --page: #aba49a; --landing-bg: #aba49a; }
      .landing-hero { background: linear-gradient(135deg, rgba(255,255,255,0.86), rgba(185,178,168,0.72)), #aba49a !important; }
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
    // Hero
    await page.screenshot({ path: `tmp_bg_${opt.name}_hero.png` });
    // Mid-page (vertical cards)
    await page.evaluate(() => document.getElementById('naming-experiences').scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(300);
    await page.screenshot({ path: `tmp_bg_${opt.name}_cards.png` });
    await page.close();
  }

  await browser.close();
  console.log('done');
})();
