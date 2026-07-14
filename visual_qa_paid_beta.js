const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:5000';
const OUT = path.join('docs', 'visual-qa', '2026-07-14-paid-beta');
fs.mkdirSync(OUT, { recursive: true });

const pages = [
  { name: 'baby-beta', url: '/baby/beta' },
  { name: 'baby-intake', url: '/baby' },
  { name: 'baby-results', url: '/baby/results?gender=Girl&style=Classic&timeless_vs_distinctive=More%20timeless&familiarity_preference=Recognizable%20but%20not%20overused&sound=Soft%20and%20lyrical&notes=Warm%2C%20classic%2C%20not%20trendy' },
  { name: 'privacy', url: '/privacy' },
];

const viewports = [
  { label: 'mobile', width: 390, height: 844, isMobile: true },
  { label: 'desktop', width: 1440, height: 1000, isMobile: false },
];

async function pageDiagnostics(page) {
  return await page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    const overflowX = Math.max(doc.scrollWidth, body.scrollWidth) - window.innerWidth;
    const buttons = Array.from(document.querySelectorAll('a.button-link, button, input, select, textarea'));
    const clipped = buttons.map((el) => {
      const r = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return {
        text: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.tagName).trim().slice(0, 80),
        tag: el.tagName,
        width: Math.round(r.width),
        height: Math.round(r.height),
        left: Math.round(r.left),
        right: Math.round(r.right),
        display: style.display,
        visible: r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && style.display !== 'none',
        offscreenX: r.left < -1 || r.right > window.innerWidth + 1,
        tooShort: r.height > 0 && r.height < 32,
      };
    }).filter((item) => item.visible && (item.offscreenX || item.tooShort));
    const footerLinks = Array.from(document.querySelectorAll('.footer-links a')).map(a => a.getAttribute('href'));
    const hasTrust = !!document.querySelector('.trust-strip, .results-disclaimer, .legal-notice');
    const ctas = Array.from(document.querySelectorAll('a.button-link, button')).map(el => (el.innerText || el.getAttribute('aria-label') || '').trim()).filter(Boolean);
    return {
      title: document.title,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      scrollWidth: Math.max(doc.scrollWidth, body.scrollWidth),
      overflowX,
      clipped,
      footerLinks,
      hasTrust,
      ctas,
    };
  });
}

(async () => {
  const browser = await chromium.launch();
  const report = [];
  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, isMobile: viewport.isMobile });
    const page = await context.newPage();
    for (const spec of pages) {
      await page.goto(BASE + spec.url, { waitUntil: 'networkidle' });
      const shot = path.join(OUT, `${spec.name}-${viewport.label}.png`);
      await page.screenshot({ path: shot, fullPage: true });
      const diag = await pageDiagnostics(page);
      report.push({ ...spec, viewport: viewport.label, screenshot: shot, diagnostics: diag });
    }
    await context.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));

  const failures = report.filter(row => row.diagnostics.overflowX > 2 || row.diagnostics.clipped.length || !row.diagnostics.hasTrust);
  fs.writeFileSync(path.join(OUT, 'summary.txt'), [
    `screenshots=${report.length}`,
    `failures=${failures.length}`,
    ...failures.map(row => `${row.name}/${row.viewport}: overflowX=${row.diagnostics.overflowX}; clipped=${row.diagnostics.clipped.length}; hasTrust=${row.diagnostics.hasTrust}`)
  ].join('\n'));

  if (failures.length) {
    console.error(JSON.stringify(failures.map(row => ({ name: row.name, viewport: row.viewport, diagnostics: row.diagnostics })), null, 2));
    process.exit(1);
  }
  console.log('visual_qa_green');
})();
