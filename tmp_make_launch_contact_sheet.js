const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const dir = path.resolve('design-references/social-launch/day1-7-launch-cards');
  const files = fs.readdirSync(dir)
    .filter(f => /^day-\d{2}-(instagram|tiktok)-.*\.png$/.test(f))
    .sort();
  const html = `<!doctype html><html><head><style>
    body{margin:0;background:#eef2f5;font-family:Arial,sans-serif;color:#0D2540;}
    h1{font-size:34px;margin:24px 28px 8px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:22px;padding:24px 28px 34px;align-items:start}.card{background:white;border-radius:18px;padding:12px;box-shadow:0 8px 28px rgba(13,37,64,.12)}
    .card img{width:100%;height:auto;display:block;border-radius:12px}.label{font-size:15px;font-weight:800;margin:10px 4px 2px;}
  </style></head><body><h1>NamEngine Day 1-7 Launch Cards</h1><div class="grid">${files.map(f=>`<div class="card"><img src="${f}"><div class="label">${f}</div></div>`).join('')}</div></body></html>`;
  const review = path.join(dir, 'LAUNCH_REVIEW.html');
  fs.writeFileSync(review, html);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1800, height: 2200 }, deviceScaleFactor: 1 });
  await page.goto('file://' + review.replace(/\\/g,'/'));
  await page.screenshot({ path: path.join(dir, 'launch-contact-sheet.png'), fullPage: true });
  const imgs = await page.$$eval('img', els => els.map(img => ({src: img.getAttribute('src'), w: img.naturalWidth, h: img.naturalHeight, ok: img.complete && img.naturalWidth > 0})));
  await browser.close();
  console.log(JSON.stringify({review, count: imgs.length, allOk: imgs.every(i=>i.ok), imgs}, null, 2));
})();
