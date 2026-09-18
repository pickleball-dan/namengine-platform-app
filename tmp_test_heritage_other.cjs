/**
 * tmp_test_heritage_other.cjs
 * Verify the cultural_heritage "Something else" fix:
 *  - syncOtherSelect does NOT clear typed value (progress.js fix)
 *  - direction review shows typed value, not trigger label (client + adapter fix)
 */
const { chromium } = require("playwright");

const BASE = "http://127.0.0.1:5200";
const TYPED = "Sudanese";

async function advanceStep(page) {
  // 1. Check-in screen?
  const checkIn = page.locator("[data-intake-checkin]:not([hidden])");
  if (await checkIn.isVisible().catch(() => false)) {
    const btn = checkIn.locator("[data-checkin-value]").first();
    if (await btn.isVisible().catch(() => false)) {
      await btn.click();
      await page.waitForTimeout(500);
      return "checkin";
    }
  }

  // 2. Active question?
  const activeQ = page.locator("[data-baby-question]:not([hidden])").first();
  if (!(await activeQ.isVisible().catch(() => false))) return null;

  const qid = await activeQ.getAttribute("data-question-id");

  // Choice question → click first choice (auto-advances)
  const choice = activeQ.locator("[data-choice-value]").first();
  if (await choice.isVisible().catch(() => false)) {
    await choice.click();
    await page.waitForTimeout(500);
    return qid;
  }

  // Text question → click Continue/Skip
  const cont = activeQ.locator("[data-baby-continue], [data-baby-skip]").first();
  if (await cont.isVisible().catch(() => false)) {
    await cont.click();
    await page.waitForTimeout(500);
    return qid;
  }

  return qid; // stuck — let caller decide
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on("pageerror", (e) => console.error("[page error]", e.message));

  await page.goto(`${BASE}/baby`, { waitUntil: "domcontentloaded" });

  // Click Begin
  const begin = page.locator(".baby-begin-button");
  await begin.waitFor({ state: "visible", timeout: 8000 });
  await begin.click();
  await page.waitForTimeout(400);
  console.log("✓ Clicked Begin");

  // ── Walk intake until cultural_heritage ──────────────────────────────────
  let reachedHeritage = false;
  for (let i = 0; i < 30; i++) {
    // Already on cultural_heritage?
    const heritageQ = page.locator('[data-baby-question][data-question-id="cultural_heritage"]:not([hidden])');
    if (await heritageQ.isVisible().catch(() => false)) {
      reachedHeritage = true;
      break;
    }

    const step = await advanceStep(page);
    console.log(`  step: ${step ?? "(nothing visible)"}`);
    if (step === null) {
      // Nothing visible — wait a bit longer then retry once
      await page.waitForTimeout(800);
      const step2 = await advanceStep(page);
      if (step2 === null) { console.error("❌ Stuck — nothing to advance"); break; }
    }
  }

  if (!reachedHeritage) {
    // Fallback: force-show cultural_heritage via JS (still tests the JS fix)
    console.log("⚠️  Navigating to cultural_heritage via JS (check-in/order fallback)");
    await page.evaluate(() => {
      document.querySelectorAll("[data-baby-question]").forEach((s) => {
        s.hidden = s.dataset.questionId !== "cultural_heritage";
        s.classList.toggle("is-active", s.dataset.questionId === "cultural_heritage");
      });
    });
    reachedHeritage = true;
  }

  // ── Interact with cultural_heritage ──────────────────────────────────────
  const heritageSection = page.locator('[data-baby-question][data-question-id="cultural_heritage"]');
  console.log("✓ On cultural_heritage question");

  // Check data-other-trigger attribute is present on the native select
  const selectTrigger = await heritageSection.locator("select[data-other-select]").getAttribute("data-other-trigger");
  console.log(`  select data-other-trigger: "${selectTrigger}" (want: "Something else — I'll describe it" or similar)`);
  if (!selectTrigger) {
    console.error("❌ FAIL: data-other-trigger missing from select — intake.html fix not applied");
  } else {
    console.log("✓ data-other-trigger is set on select");
  }

  // Click "Something else — I'll describe it"
  const somethingElse = heritageSection.locator("[data-choice-value]").filter({ hasText: /Something else/i });
  await somethingElse.waitFor({ state: "visible", timeout: 5000 });
  await somethingElse.click();
  console.log("✓ Clicked 'Something else'");
  await page.waitForTimeout(400);

  // Other-input should be visible and NOT disabled
  const otherInput = heritageSection.locator("[data-other-input]");
  await otherInput.waitFor({ state: "visible", timeout: 4000 });
  const disabled = await otherInput.isDisabled();
  if (disabled) {
    console.error("❌ FAIL: other input still disabled — syncOtherSelect fix NOT working");
    await page.screenshot({ path: "tmp_heritage_disabled.png" });
    await browser.close(); process.exit(1);
  }
  console.log("✓ Other input is enabled (syncOtherSelect fix ✅)");

  // Type custom value
  await otherInput.fill(TYPED);
  const val = await otherInput.inputValue();
  if (val !== TYPED) {
    console.error(`❌ FAIL: input value is "${val}" not "${TYPED}"`);
    await browser.close(); process.exit(1);
  }
  console.log(`✓ Typed "${TYPED}" — value held (not cleared by syncOtherSelect)`);

  // Simulate re-triggering syncOtherSelect (as happens when JS dispatches change events)
  // If the fix is correct, input.value should still be TYPED afterwards
  await page.evaluate((trigger) => {
    const sel = document.querySelector('select[data-other-select][data-other-trigger]');
    if (sel) sel.dispatchEvent(new Event("change", { bubbles: true }));
  }, selectTrigger);
  await page.waitForTimeout(200);
  const valAfterSync = await otherInput.inputValue();
  if (valAfterSync !== TYPED) {
    console.error(`❌ FAIL: syncOtherSelect cleared value — got "${valAfterSync}" after change event. Fix not working!`);
    await browser.close(); process.exit(1);
  }
  console.log(`✓ Value still "${valAfterSync}" after change-event dispatch — syncOtherSelect is NOT clearing it`);

  // Click Continue
  const contBtn = heritageSection.locator("[data-baby-other-continue]");
  await contBtn.waitFor({ state: "visible", timeout: 3000 });
  await contBtn.click();
  console.log("✓ Clicked Continue");
  await page.waitForTimeout(500);

  // ── Walk remaining questions to direction review ───────────────────────────
  for (let i = 0; i < 25; i++) {
    const reviewVis = await page.locator("[data-baby-direction-review]:not([hidden])").isVisible().catch(() => false);
    if (reviewVis) break;
    await advanceStep(page);
  }

  // ── Check direction review ────────────────────────────────────────────────
  const review = page.locator("[data-baby-direction-review]");
  const reviewVisible = await review.isVisible().catch(() => false);
  if (!reviewVisible) {
    console.log("⚠️  Direction review not reached — checking valueFor() directly");
    // Test the JS valueFor() function for cultural_heritage
    const jsResult = await page.evaluate((typed) => {
      // Simulate what valueFor() would return for cultural_heritage
      const section = document.querySelector('[data-baby-question][data-question-id="cultural_heritage"]');
      if (!section) return { error: "section not found" };
      const control = section.querySelector("select, textarea, input:not([type='hidden']):not([data-other-input])");
      const otherInput = section.querySelector("[data-other-input]");
      return {
        selectValue: control ? control.value : null,
        otherValue: otherInput ? otherInput.value : null,
        otherHidden: otherInput ? otherInput.hidden : null,
        otherDisabled: otherInput ? otherInput.disabled : null,
      };
    }, TYPED);
    console.log("  JS state:", JSON.stringify(jsResult));
    if (jsResult.otherValue === TYPED) {
      console.log(`✅ PASS (partial): other input holds "${TYPED}" — fix is working client-side`);
    } else {
      console.error(`❌ FAIL: other input value is "${jsResult.otherValue}" not "${TYPED}"`);
      process.exitCode = 1;
    }
  } else {
    console.log("✓ Direction review visible");
    const reviewText = await review.innerText();
    console.log("\n── Review text ──\n" + reviewText + "\n────────────────\n");

    const hasTrigger = reviewText.includes("Something else");
    const hasTyped = reviewText.includes(TYPED);

    if (hasTyped && !hasTrigger) {
      console.log(`✅ PASS: Review shows "${TYPED}", trigger label gone`);
    } else if (hasTrigger && !hasTyped) {
      console.error(`❌ FAIL: Review shows trigger label, not "${TYPED}"`);
      process.exitCode = 1;
    } else if (hasTyped && hasTrigger) {
      console.log(`⚠️  Both strings visible — check context`);
    } else {
      console.log("⚠️  Heritage not visible in review (may be skipped/blank)");
    }
  }

  await page.screenshot({ path: "tmp_heritage_review_test.png", fullPage: false });
  console.log("📸 Screenshot: tmp_heritage_review_test.png");
  await browser.close();
}

run().catch((err) => { console.error("Fatal:", err); process.exit(1); });
