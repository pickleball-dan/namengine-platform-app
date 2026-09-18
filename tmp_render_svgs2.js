const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const imgDir = 'C:/Users/dnorm/.openclaw/workspace/namengine_platform_app/static/images/';

const svgs = [
  { file: 'namengine.svg',           label: 'namengine',           bg: '#ffffff' },
  { file: 'namengine-baby.svg',      label: 'namengine-baby',      bg: '#fff5f3' },
  { file: 'namengine-pets.svg',      label: 'namengine-pets',      bg: '#fff9f0' },
  { file: 'namengine-biz.svg',       label: 'namengine-biz',       bg: '#0e1e3c' },
  { file: 'namengine-baby-icon.svg', label: 'namengine-baby-icon', bg: '#fff5f3' },
  { file: 'namengine-pets-icon.svg', label: 'namengine-pets-icon', bg: '#fff9f0' },
  { file: 'namengine-biz-icon.svg',  label: 'namengine-biz-icon',  bg: '#0e1e3c' },
  { file: 'namengine-icon.svg',      label: 'namengine-icon',      bg: '#ffffff' },
  { file: 'baby-logo.svg',           label: 'baby-logo',           bg: '#fff5f3' },
  { file: 'business-logo.svg',       label: 'business-logo',       bg: '#0e1e3c' },
  { file: 'character-logo.svg',      label: 'character-logo',      bg: '#ffffff' },
  { file: 'app-icon.svg',            label: 'app-icon',            bg: '#ffffff' },
  { file: 'favicon.svg',             label: 'favicon',             bg: '#ffffff' },
  { file: 'baby-share.svg',          label: 'baby-share',          bg: '#fff5f3' },
];

(async () => {
  const b = await chromium.launch();

  for (const { file, label, bg } of svgs) {
    const svgContent = fs.readFileSync(path.join(imgDir, file), 'utf8');
    const page = await b.newPage();
    await page.setViewportSize({ width: 600, height: 300 });
    const html = `<!DOCTYPE html><html><body style="margin:0;background:${bg};display:flex;align-items:center;justify-content:center;height:300px;">${svgContent}</body></html>`;
    await page.setContent(html, { waitUntil: 'load' });
    // Scale the SVG to fit nicely
    await page.addStyleTag({ content: 'body > svg { max-width: 560px; max-height: 260px; width: auto; height: auto; }' });
    await page.waitForTimeout(300);
    const out = `tmp_logo2_${label}.png`;
    await page.screenshot({ path: out });
    await page.close();
    console.log('done:', out);
  }

  await b.close();
})();
