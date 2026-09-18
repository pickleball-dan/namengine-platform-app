// Test: paywall modal fires on locked actions; no redirect
// Uses already-generated session IDs from earlier tests.
const { chromium } = require('playwright');

const SESSIONS = [
  { label: 'baby',     url: 'http://127.0.0.1:5000/results/session/baby-7aaca470e7fa' },
  { label: 'pet',      url: 'http://127.0.0.1:5000/results/session/pet-ff8289c94bdc'  },
  { label: 'business', url: 'http://127.0.0.1:5000/results/session/business-5ed36fba35d8' },
];

(async () => {
  const br = await chromium.launch();
  let allPassed = true;

  for (const sess of SESSIONS) {
    // Fresh context = no cookies = unlocked=false
    const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } });
    const pg = await ctx.newPage();

    await pg.goto(sess.url, { waitUntil: 'domcontentloaded', timeout: 12000 });
    await pg.waitForTimeout(800);

    // --- Test 1: Love reaction button triggers modal, not a redirect ---
    const loveBtn = await pg.$('.reaction-row button:first-child');
    if (!loveBtn) {
      console.log(`[${sess.label}] SKIP: no reaction button found`);
    } else {
      const urlBefore = pg.url();
      await loveBtn.click();
      await pg.waitForTimeout(600);
      const urlAfter = pg.url();
      const modalVisible = await pg.$eval(
        '.access-gate-modal-backdrop',
        el => el && !el.hidden
      ).catch(() => false);
      const redirected = urlAfter !== urlBefore && urlAfter.includes('/access');
      const pass1 = modalVisible && !redirected;
      console.log(`[${sess.label}] Love btn → modal=${modalVisible} redirect=${redirected} → ${pass1 ? 'PASS' : 'FAIL'}`);
      if (!pass1) allPassed = false;

      // Screenshot with modal open
      await pg.screenshot({ path: `qa-artifacts/paywall-hero-fix/modal-${sess.label}.png`, fullPage: false });

      // Close modal
      const closeBtn = await pg.$('[data-access-gate-close]');
      if (closeBtn) { await closeBtn.click(); await pg.waitForTimeout(300); }
    }

    // --- Test 2: No reaction button triggers a server redirect to /access ---
    const noBtn = await pg.$('.reaction-row button:last-child');
    if (noBtn) {
      const urlBefore2 = pg.url();
      await noBtn.click();
      await pg.waitForTimeout(400);
      const redirected2 = pg.url() !== urlBefore2 && pg.url().includes('/access');
      const modal2 = await pg.$eval('.access-gate-modal-backdrop', el => el && !el.hidden).catch(() => false);
      const pass2 = modal2 && !redirected2;
      console.log(`[${sess.label}] No btn  → modal=${modal2}  redirect=${redirected2} → ${pass2 ? 'PASS' : 'FAIL'}`);
      if (!pass2) allPassed = false;
      const closeBtn2 = await pg.$('[data-access-gate-close]');
      if (closeBtn2) { await closeBtn2.click(); await pg.waitForTimeout(300); }
    }

    // --- Test 3: Unlock link inside modal points to /access, not external ---
    const unlockLink = await pg.$('[data-access-gate-unlock]');
    if (unlockLink) {
      const href = await unlockLink.getAttribute('href');
      const pass3 = href && href.includes('/access');
      console.log(`[${sess.label}] Unlock href="${href}" → ${pass3 ? 'PASS' : 'FAIL'}`);
      if (!pass3) allPassed = false;
    }

    await ctx.close();
  }

  await br.close();
  console.log('\n' + (allPassed ? '✅ ALL PASSED' : '❌ SOME FAILURES'));
  process.exit(allPassed ? 0 : 1);
})();
