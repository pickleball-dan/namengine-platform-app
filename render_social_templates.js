const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const dir = path.resolve('design-references/social-launch/batch1-canva-templates');
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.svg'));
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1200, height: 2000 }, deviceScaleFactor: 1 });
  for (const file of files) {
    const svgPath = path.join(dir, file);
    const pngPath = path.join(dir, file.replace(/\.svg$/, '.png'));
    const svg = fs.readFileSync(svgPath, 'utf8');
    const m = svg.match(/<svg[^>]*width="(\d+)"[^>]*height="(\d+)"/);
    const width = m ? parseInt(m[1], 10) : 1080;
    const height = m ? parseInt(m[2], 10) : 1350;
    await page.setViewportSize({ width, height });
    await page.setContent(`<!doctype html><html><body style="margin:0;background:white">${svg}</body></html>`);
    await page.screenshot({ path: pngPath, clip: { x: 0, y: 0, width, height } });
  }
  await browser.close();
  console.log(`Rendered ${files.length} PNG previews`);
})();
