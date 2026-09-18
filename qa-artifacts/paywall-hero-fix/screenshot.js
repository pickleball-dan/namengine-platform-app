const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const br = await chromium.launch();
  const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } });

  // --- Screenshot 1: Hero text on access page ---
  const p1 = await ctx.newPage();
  await p1.goto('http://127.0.0.1:5000/business/access', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await p1.waitForTimeout(600);
  await p1.screenshot({ path: 'qa-artifacts/paywall-hero-fix/01-access-hero.png', fullPage: false });
  console.log('01-access-hero done');
  await p1.close();

  // --- Screenshot 2: Intake page ---
  const p2 = await ctx.newPage();
  await p2.goto('http://127.0.0.1:5000/business', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await p2.waitForTimeout(600);
  await p2.screenshot({ path: 'qa-artifacts/paywall-hero-fix/02-intake.png', fullPage: false });
  console.log('02-intake done, url:', p2.url());
  await p2.close();

  await br.close();
})();
