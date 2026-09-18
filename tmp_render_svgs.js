const { chromium } = require('playwright');
const base = 'C:/Users/dnorm/.openclaw/workspace/namengine_platform_app/static/images/';

const svgs = [
  'namengine.svg',
  'namengine-baby.svg',
  'namengine-pets.svg',
  'namengine-biz.svg',
  'namengine-baby-icon.svg',
  'namengine-pets-icon.svg',
  'namengine-biz-icon.svg',
  'namengine-icon.svg',
  'baby-logo.svg',
  'business-logo.svg',
  'character-logo.svg',
  'app-icon.svg',
  'favicon.svg',
  'baby-share.svg',
];

(async () => {
  const b = await chromium.launch();
  for (const svg of svgs) {
    const page = await b.newPage();
    await page.setViewportSize({ width: 600, height: 300 });
    const html = `<html><body style="background:#f0f0f0;display:flex;align-items:center;justify-content:center;height:300px;margin:0;"><img src="file:///${base}${svg}" style="max-width:560px;max-height:260px;" /></body></html>`;
    await page.setContent(html);
    await page.waitForTimeout(400);
    const out = 'tmp_logo_' + svg.replace('.svg', '.png');
    await page.screenshot({ path: out });
    await page.close();
    console.log('done:', out);
  }
  await b.close();
})();
