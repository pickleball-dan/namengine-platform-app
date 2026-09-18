const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const base = 'http://127.0.0.1:5000';
const outDir = path.join(process.cwd(), 'qa-artifacts', 'progress-overlay-label-removal-20260818-1048');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', msg => { if (['error','warning'].includes(msg.type())) consoleErrors.push(`${msg.type()}: ${msg.text()}`); });
  const response = await page.goto(base + '/business', { waitUntil: 'networkidle', timeout: 30000 });
  await page.evaluate(() => {
    const overlay = document.querySelector('[data-progress-overlay]');
    if (overlay) overlay.hidden = false;
  });
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, 'business-progress-overlay-mobile-full.png'), fullPage: true });
  const panel = page.locator('.progress-panel').first();
  if (await panel.count()) await panel.screenshot({ path: path.join(outDir, 'business-progress-overlay-mobile-panel.png') });
  const diag = await page.evaluate(() => {
    const doc = document.documentElement;
    const text = document.body.innerText;
    return {
      status: document.title,
      horizontalOverflow: doc.scrollWidth > doc.clientWidth + 1,
      hasProgressVisualLabel: Boolean(document.querySelector('.progress-visual-label')),
      hasIdentityFitText: text.includes('Identity fit') || text.includes('IDENTITY FIT'),
      consoleTextSample: text.slice(0, 500),
    };
  });
  await browser.close();
  console.log(JSON.stringify({ outDir, status: response?.status() ?? null, consoleErrors, ...diag }, null, 2));
})();
