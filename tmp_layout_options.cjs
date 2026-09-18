const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 900 });

  async function shot(label, css) {
    await page.goto('http://localhost:5000', { waitUntil: 'domcontentloaded', timeout: 10000 });
    await page.waitForTimeout(500);
    await page.evaluate((css) => {
      const s = document.createElement('style');
      s.textContent = css;
      document.head.appendChild(s);
      document.getElementById('sample-report').scrollIntoView({ block: 'center' });
    }, css);
    await page.waitForTimeout(350);
    await page.screenshot({ path: `tmp_layout_${label}.png` });
  }

  // Option A: Centered heading + wider card (700px)
  await shot('A', `
    .landing-sample-section .landing-section-head {
      max-width: 100%; text-align: center;
    }
    .landing-sample-section .landing-section-head p,
    .landing-sample-section .landing-section-head h2 { max-width: 640px; margin-left: auto; margin-right: auto; }
    .landing-sample-card { max-width: 700px; }
  `);

  // Option B: Two-column — copy left, card right
  await shot('B', `
    .landing-sample-section > * { max-width: 1100px; margin-left: auto; margin-right: auto; }
    .landing-sample-section {
      display: grid !important;
      grid-template-columns: 1fr 520px;
      align-items: start;
      gap: 48px 64px;
      max-width: 1100px;
      margin-left: auto;
      margin-right: auto;
    }
    .landing-sample-section .landing-section-head { max-width: 100%; padding-top: 32px; }
    .landing-sample-card { margin: 0; max-width: 100%; }
  `);

  // Option C: Full-width card, centered heading, card edge-to-edge at 820px
  await shot('C', `
    .landing-sample-section .landing-section-head {
      max-width: 100%; text-align: center;
    }
    .landing-sample-section .landing-section-head p,
    .landing-sample-section .landing-section-head h2 { max-width: 640px; margin-left: auto; margin-right: auto; }
    .landing-sample-card {
      max-width: 820px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-template-rows: auto 1fr auto;
    }
    .lsc-header { grid-column: 1 / -1; }
    .lsc-body {
      grid-column: 1;
      border-right: 1px solid rgba(255,107,87,0.14);
      padding-right: 20px;
    }
    .lsc-footer { grid-column: 1 / -1; }
    .lsc-body + .lsc-footer { display: none; }
  `);

  await browser.close();
  console.log('done');
})();
