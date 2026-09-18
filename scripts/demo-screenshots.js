/**
 * scripts/demo-screenshots.js
 * Standalone screenshot capture for the taste-history + homepage-return demo.
 * Not part of the test suite — run this to preview before committing changes.
 *
 * Usage:
 *   BASE_URL=http://localhost:5000 node scripts/demo-screenshots.js
 */
'use strict';
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE = process.env.BASE_URL || 'http://localhost:5000';
const OUT = path.join(__dirname, '..', 'tmp_demo_screenshots');
const SCRIPT_PATH = path.join(__dirname, '..', 'static', 'js', 'homepage-return.js');

const SEED = {
  'namengine.baby.tasteHistory.v1': JSON.stringify([{
    sessionId: 'baby-620e7c9afc86',
    title: 'Baby Round 1',
    context: '8 names · 6 direction selections',
    listUrl: '/results/session/baby-620e7c9afc86',
    shareUrl: '/share/baby-620e7c9afc86',
    lovedNames: ['Elowen', 'Saoirse', 'Niamh'],
    savedAt: '2026-09-01T10:00:00.000Z',
  }]),
  'namengine.pet.tasteHistory.v1': JSON.stringify([{
    sessionId: 'pet-0275b847cbed',
    title: 'Pet Round 1',
    context: '8 names · 5 direction selections',
    listUrl: '/results/session/pet-0275b847cbed',
    shareUrl: '/share/pet-0275b847cbed',
    lovedNames: ['Calantha', 'Liora', 'Nimue', 'Calithia', 'Neralia'],
    savedAt: '2026-09-01T10:00:00.000Z',
  }]),
  'namengine.business.tasteHistory.v1': JSON.stringify([{
    sessionId: 'business-4b3f47d6ea31',
    title: 'Business Round 1',
    context: '8 names · 7 direction selections',
    listUrl: '/results/session/business-4b3f47d6ea31',
    shareUrl: '/share/business-4b3f47d6ea31',
    lovedNames: ['Northmark', 'Veritas', 'Crestline'],
    savedAt: '2026-09-01T10:00:00.000Z',
  }]),
};

async function seed(page) {
  await page.evaluate((s) => {
    for (const [k, v] of Object.entries(s)) window.localStorage.setItem(k, v);
  }, SEED);
}

async function capture(page, filename, opts = {}) {
  const filepath = path.join(OUT, filename);
  if (opts.element) {
    await page.locator(opts.element).screenshot({ path: filepath });
  } else {
    const clip = opts.clip || undefined;
    await page.screenshot({ path: filepath, clip, fullPage: opts.fullPage });
  }
  console.log('  ✓', filename);
  return filepath;
}

async function run() {
  fs.mkdirSync(OUT, { recursive: true });
  console.log('\nNamEngine Demo Screenshots');
  console.log('BASE_URL:', BASE);
  console.log('Output:', OUT, '\n');

  const browser = await chromium.launch({ headless: true });

  // ── MOBILE (390×844) ──────────────────────────────────────────────────────
  console.log('── Mobile (390×844) ──');
  const mCtx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mp = await mCtx.newPage();

  // 1. Pet intake taste panel — returning user
  console.log(' [1] Pet taste panel');
  await mp.goto(`${BASE}/pet`);
  await seed(mp);
  await mp.reload();
  await mp.locator('.taste-history-panel').waitFor({ state: 'visible', timeout: 10000 });
  await capture(mp, '01-mobile-pet-taste-panel.png', { element: '.taste-history-panel' });

  // 2. Pet "Review favorites" dialog
  console.log(' [2] Pet dialog');
  await mp.locator('[data-taste-history-open]').click();
  await mp.locator('[data-taste-history-dialog]').waitFor({ state: 'visible' });
  await mp.waitForTimeout(200);
  await capture(mp, '02-mobile-pet-dialog.png', { clip: { x: 0, y: 0, width: 390, height: 844 } });
  await mp.locator('[data-taste-history-close]').click();

  // 3. Baby intake taste panel
  console.log(' [3] Baby taste panel');
  await mp.goto(`${BASE}/baby`);
  await seed(mp);
  await mp.reload();
  await mp.locator('.taste-history-panel').waitFor({ state: 'visible', timeout: 10000 });
  await capture(mp, '03-mobile-baby-taste-panel.png', { element: '.taste-history-panel' });

  // 4. Business intake taste panel
  console.log(' [4] Business taste panel');
  await mp.goto(`${BASE}/business`);
  await seed(mp);
  await mp.reload();
  await mp.locator('.taste-history-panel').waitFor({ state: 'visible', timeout: 10000 });
  await capture(mp, '04-mobile-business-taste-panel.png', { element: '.taste-history-panel' });

  // 5. Homepage return hook — mobile
  console.log(' [5] Homepage return hook (mobile)');
  await mp.goto(`${BASE}/`);
  await seed(mp);
  await mp.addScriptTag({ path: SCRIPT_PATH });
  await mp.waitForTimeout(400);
  const hookM = mp.locator('#homepage-return-hook');
  await hookM.waitFor({ state: 'visible', timeout: 8000 });
  await capture(mp, '05-mobile-homepage-return.png', { clip: { x: 0, y: 0, width: 390, height: 900 } });

  await mCtx.close();

  // ── DESKTOP (1280×800) ────────────────────────────────────────────────────
  console.log('\n── Desktop (1280×800) ──');
  const dCtx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const dp = await dCtx.newPage();

  // 6. Homepage return hook — desktop (top portion of page)
  console.log(' [6] Homepage return hook (desktop)');
  await dp.goto(`${BASE}/`);
  await seed(dp);
  await dp.addScriptTag({ path: SCRIPT_PATH });
  await dp.waitForTimeout(400);
  const hookD = dp.locator('#homepage-return-hook');
  await hookD.waitFor({ state: 'visible', timeout: 8000 });
  // Capture from top of page down to include the hook section in context
  await capture(dp, '06-desktop-homepage-return.png', { clip: { x: 0, y: 0, width: 1280, height: 900 } });

  // 7. Pet taste panel — desktop
  console.log(' [7] Pet taste panel (desktop)');
  await dp.goto(`${BASE}/pet`);
  await seed(dp);
  await dp.reload();
  await dp.locator('.taste-history-panel').waitFor({ state: 'visible', timeout: 10000 });
  await capture(dp, '07-desktop-pet-taste-panel.png', { element: '.taste-history-panel' });

  await dCtx.close();
  await browser.close();

  console.log(`\nDone. ${fs.readdirSync(OUT).length} screenshots in:\n  ${OUT}\n`);
}

run().catch((err) => {
  console.error('\n✗ Screenshot script failed:', err.message);
  process.exit(1);
});
