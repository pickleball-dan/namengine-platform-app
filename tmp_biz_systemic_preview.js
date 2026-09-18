const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const b = await chromium.launch();
  const svg = fs.readFileSync('static/images/namengine-biz.svg', 'utf8');
  const scaledSvg = svg.replace('<svg ', '<svg style="max-width:500px;height:auto;filter:brightness(0) invert(1);" ');

  // Show before/after side by side on dark background
  const html = `<!DOCTYPE html><html><body style="margin:0;background:#0e1e3c;display:flex;flex-direction:column;gap:32px;align-items:center;justify-content:center;min-height:400px;font-family:sans-serif;padding:32px;">
    <div style="text-align:center;">
      <div style="color:rgba(255,255,255,.4);font-size:11px;margin-bottom:10px;text-transform:uppercase;letter-spacing:.08em;">Before (invisible)</div>
      ${svg.replace('<svg ', '<svg style="max-width:500px;height:auto;" ')}
    </div>
    <div style="border-top:1px solid rgba(255,255,255,.1);width:100%;"></div>
    <div style="text-align:center;">
      <div style="color:rgba(255,255,255,.4);font-size:11px;margin-bottom:10px;text-transform:uppercase;letter-spacing:.08em;">After — CSS filter:brightness(0)invert(1)</div>
      ${scaledSvg}
    </div>
  </body></html>`;

  const page = await b.newPage();
  await page.setViewportSize({ width: 600, height: 420 });
  await page.setContent(html, { waitUntil: 'load' });
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp_biz_systemic_result.png' });
  await page.close();
  await b.close();
  console.log('done');
})();
