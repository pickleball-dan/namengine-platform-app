const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const b = await chromium.launch();
  const page = await b.newPage();

  // Test 1: SVG as <img> tag on dark background
  const html1 = `<html><body style="background:#0e1e3c;margin:0;padding:20px;">
    <p style="color:white;font-size:11px;margin:0 0 8px">Via img tag:</p>
    <img src="http://localhost:5000/static/images/namengine-biz-reversed.svg" style="width:300px;height:auto;display:block;">
    <p style="color:white;font-size:11px;margin:8px 0">Via inline SVG:</p>
    ${fs.readFileSync('static/images/namengine-biz-reversed.svg','utf8').replace('<svg ','<svg style="width:300px;height:auto;display:block;" ')}
  </body></html>`;

  await page.setViewportSize({ width: 400, height: 300 });
  await page.setContent(html1, { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'tmp_svg_img_vs_inline.png' });
  await page.close();
  await b.close();
  console.log('done');
})();
