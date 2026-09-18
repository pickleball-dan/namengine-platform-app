const { chromium } = require('playwright');

(async () => {
  const br = await chromium.launch();

  // --- Business: first question is business_description (textarea) ---
  const ctx1 = await br.newContext({ viewport: { width: 390, height: 844 } });
  const p1 = await ctx1.newPage();
  await p1.goto('http://127.0.0.1:5000/business', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await p1.waitForTimeout(800);

  // Click begin button (same class across all verticals)
  await p1.click('.baby-begin-button');
  await p1.waitForTimeout(600);

  // First question is business_description (textarea) — click to focus
  await p1.click('textarea#business_description');
  await p1.waitForTimeout(400);

  // Screenshot: chips visible, empty field
  await p1.screenshot({ path: 'qa-artifacts/paywall-hero-fix/assist-business-chips.png', fullPage: false });
  console.log('business chips done');

  // Type text to trigger encouragement (>60 chars = "Good detail — this helps ✓")
  await p1.fill('textarea#business_description', 'We help landscape and pool contractors source premium hardscape materials across the Southwest region');
  await p1.locator('textarea#business_description').dispatchEvent('input');
  await p1.waitForTimeout(300);
  await p1.screenshot({ path: 'qa-artifacts/paywall-hero-fix/assist-business-encouragement.png', fullPage: false });
  console.log('business encouragement done');
  await ctx1.close();

  // --- Pet ---
  const ctx2 = await br.newContext({ viewport: { width: 390, height: 844 } });
  const p2 = await ctx2.newPage();
  await p2.goto('http://127.0.0.1:5000/pet', { waitUntil: 'domcontentloaded', timeout: 10000 });
  await p2.waitForTimeout(800);
  await p2.click('.baby-begin-button');
  await p2.waitForTimeout(600);

  // Pet guided flow — click through choice questions until we hit pet_details textarea
  for (let i = 0; i < 12; i++) {
    const ta = await p2.$('textarea#pet_details');
    if (ta) { await ta.click(); break; }
    // Pick first available choice card
    const choice = await p2.$('[data-choice-value]:not(.is-selected)');
    if (choice) { await choice.click(); await p2.waitForTimeout(400); continue; }
    // Click Next if no choice picked
    const nextBtn = await p2.$('[data-pet-next]:not([hidden])');
    if (nextBtn) { await nextBtn.click(); await p2.waitForTimeout(400); }
  }
  await p2.screenshot({ path: 'qa-artifacts/paywall-hero-fix/assist-pet-chips.png', fullPage: false });
  console.log('pet done');
  await ctx2.close();

  await br.close();
})();
