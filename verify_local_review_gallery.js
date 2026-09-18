const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const file = 'file:///' + path.resolve('design-references/social-launch/batch1-canva-templates/LOCAL_REVIEW.html').replace(/\\/g, '/');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1200 }, deviceScaleFactor: 1 });
  await page.goto(file, { waitUntil: 'load' });
  const imgs = await page.$$eval('img', imgs => imgs.map(i => ({
    src: i.getAttribute('src'),
    w: i.naturalWidth,
    h: i.naturalHeight,
    complete: i.complete,
    ok: i.complete && i.naturalWidth > 0 && i.naturalHeight > 0,
  })));
  console.log(JSON.stringify({ file, count: imgs.length, allOk: imgs.every(i => i.ok), imgs }, null, 2));
  await page.screenshot({ path: 'design-references/social-launch/batch1-canva-templates/local-review-screenshot.png', fullPage: false });
  await browser.close();
})();
