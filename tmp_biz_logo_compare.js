const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const b = await chromium.launch();

  // Light background (homepage use)
  const svgLight = fs.readFileSync('static/images/namengine-biz.svg', 'utf8');
  const pageLight = await b.newPage();
  await pageLight.setViewportSize({ width: 700, height: 200 });
  await pageLight.setContent(`<!DOCTYPE html><html><body style="margin:0;background:#ffffff;display:flex;align-items:center;justify-content:center;height:200px;">${svgLight.replace('<svg ', '<svg style="max-width:640px;height:auto;" ')}</body></html>`);
  await pageLight.waitForTimeout(400);
  await pageLight.screenshot({ path: 'tmp_biz_light_bg.png' });
  await pageLight.close();

  // Dark background (detail/results page use) — reversed SVG
  const svgDark = fs.readFileSync('static/images/namengine-biz-reversed.svg', 'utf8');
  const pageDark = await b.newPage();
  await pageDark.setViewportSize({ width: 700, height: 200 });
  await pageDark.setContent(`<!DOCTYPE html><html><body style="margin:0;background:#0e1e3c;display:flex;align-items:center;justify-content:center;height:200px;">${svgDark.replace('<svg ', '<svg style="max-width:640px;height:auto;" ')}</body></html>`);
  await pageDark.waitForTimeout(400);
  await pageDark.screenshot({ path: 'tmp_biz_dark_bg.png' });
  await pageDark.close();

  await b.close();
  console.log('done');
})();
