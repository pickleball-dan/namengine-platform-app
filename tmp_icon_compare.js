const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const b = await chromium.launch();
  const page = await b.newPage();

  const newIcon = fs.readFileSync('static/images/namengine-icon.svg', 'utf8');
  const scaledIcon = newIcon.replace('<svg ', '<svg width="80" height="80" ');

  const html = `<!DOCTYPE html>
<html><body style="margin:0;background:#fff;display:flex;gap:48px;align-items:center;justify-content:center;height:300px;font-family:sans-serif;">
  <div style="text-align:center;">
    <div style="color:#bbb;font-size:11px;margin-bottom:10px;text-decoration:line-through;">app-icon.svg — DELETED</div>
    <div style="width:100px;height:100px;background:#f0f0f0;border-radius:22px;display:flex;align-items:center;justify-content:center;color:#bbb;font-size:11px;">gone</div>
  </div>
  <div style="font-size:28px;color:#ccc;">→</div>
  <div style="text-align:center;">
    <div style="color:#333;font-size:11px;font-weight:700;margin-bottom:10px;">namengine-icon.svg — REPLACES IT</div>
    <div style="width:100px;height:100px;background:#f0f0f0;border-radius:22px;display:flex;align-items:center;justify-content:center;">${scaledIcon}</div>
  </div>
</body></html>`;

  await page.setViewportSize({ width: 460, height: 300 });
  await page.setContent(html, { waitUntil: 'load' });
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'tmp_icon_compare.png' });
  await b.close();
  console.log('done');
})();
