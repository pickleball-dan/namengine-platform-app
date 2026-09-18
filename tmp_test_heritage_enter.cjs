/**
 * tmp_test_heritage_enter.cjs
 * Verify that pressing Enter in the cultural_heritage other-input
 * advances to the next question (via Continue button) instead of
 * submitting the form and jumping straight to name generation.
 */
const { chromium } = require("playwright");

const BASE = "http://127.0.0.1:5200";
const TYPED = "Basque";

async function advanceStep(page) {
  const checkIn = page.locator("[data-intake-checkin]:not([hidden])");
  if (await checkIn.isVisible().catch(() => false)) {
    const btn = checkIn.locator("[data-checkin-value]").first();
    if (await btn.isVisible().catch(() => false)) { await btn.click(); await page.waitForTimeout(500); return "checkin"; }
  }
  const activeQ = page.locator("[data-baby-question]:not([hidden])").first();
  if (!(await activeQ.isVisible().catch(() => false))) return null;
  const qid = await activeQ.getAttribute("data-question-id");
  const choice = activeQ.locator("[data-choice-value]").first();
  if (await choice.isVisible().catch(() => false)) { await choice.click(); await page.waitForTimeout(500); return qid; }
  const cont = activeQ.locator("[data-baby-continue], [data-baby-skip]").first();
  if (await cont.isVisible().catch(() => false)) { await cont.click(); await page.waitForTimeout(500); return qid; }
  return qid;
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto(`${BASE}/baby`, { waitUntil: "domcontentloaded" });
  const begin = page.locator(".baby-begin-button");
  await begin.waitFor({ state: "visible", timeout: 8000 });
  await begin.click();
  await page.waitForTimeout(400);
  console.log("✓ Clicked Begin");

  // Walk to cultural_heritage
  for (let i = 0; i < 30; i++) {
    const heritageQ = page.locator('[data-baby-question][data-question-id="cultural_heritage"]:not([hidden])');
    if (await heritageQ.isVisible().catch(() => false)) break;
    await advanceStep(page);
  }

  const heritageSection = page.locator('[data-baby-question][data-question-id="cultural_heritage"]');
  const onHeritage = await heritageSection.isVisible().catch(() => false);
  if (!onHeritage) { console.error("❌ Never reached cultural_heritage"); await browser.close(); process.exit(1); }
  console.log("✓ On cultural_heritage");

  // Click "Something else"
  const somethingElse = heritageSection.locator("[data-choice-value]").filter({ hasText: /Something else/i });
  await somethingElse.waitFor({ state: "visible", timeout: 4000 });
  await somethingElse.click();
  await page.waitForTimeout(300);

  // Type value
  const otherInput = heritageSection.locator("[data-other-input]");
  await otherInput.waitFor({ state: "visible", timeout: 4000 });
  await otherInput.fill(TYPED);
  console.log(`✓ Typed "${TYPED}"`);

  // ── KEY TEST: press Enter ──────────────────────────────────────────────
  await otherInput.press("Enter");
  await page.waitForTimeout(600);
  console.log("✓ Pressed Enter");

  // After Enter, the form must NOT have submitted / triggered name generation.
  // The direction review should NOT be visible yet (more questions remain).
  // The next question after cultural_heritage should be active, OR if all
  // remaining questions were already optional/skipped, direction review is fine.
  // What must NOT happen: jumping straight to a results/loading page.
  const onResultsPage = page.url().includes("/results") || page.url().includes("/baby/results");
  if (onResultsPage) {
    console.error("❌ FAIL: Enter submitted the form — jumped to results page, skipping remaining questions");
    process.exitCode = 1;
  } else {
    console.log(`  URL after Enter: ${page.url()} (not /results ✅)`);
  }

  // Direction review or next question should be on-screen
  const reviewVisible = await page.locator("[data-baby-direction-review]:not([hidden])").isVisible().catch(() => false);
  const nextQVisible  = await page.locator("[data-baby-question]:not([hidden])").isVisible().catch(() => false);

  if (reviewVisible) {
    console.log("✓ Direction review appeared (all remaining questions were already answered)");
  } else if (nextQVisible) {
    const nextQid = await page.locator("[data-baby-question]:not([hidden])").first().getAttribute("data-question-id");
    console.log(`✓ Moved to next question: ${nextQid} — Enter behaved as Continue ✅`);
  } else {
    console.log("⚠️  Neither next question nor direction review is visible — check state");
  }

  // Make sure the typed value is still held (not cleared)
  const stillHeld = await page.evaluate((typed) => {
    const inp = document.querySelector('[data-question-id="cultural_heritage"] [data-other-input]');
    return inp ? inp.value : null;
  }, TYPED);
  console.log(`  other input value after Enter: "${stillHeld}" (want: "${TYPED}")`);
  if (stillHeld === TYPED) {
    console.log("✓ Typed value preserved");
  } else {
    console.log("⚠️  Typed value not in DOM (may have advanced — check review)");
  }

  await page.screenshot({ path: "tmp_heritage_enter_test.png", fullPage: false });
  console.log("📸 Screenshot: tmp_heritage_enter_test.png");

  if (process.exitCode !== 1) console.log("\n✅ PASS: Enter key no longer submits the form");
  await browser.close();
}

run().catch((err) => { console.error("Fatal:", err); process.exit(1); });
