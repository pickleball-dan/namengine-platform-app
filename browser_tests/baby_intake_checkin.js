const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = process.env.NAMENGINE_BROWSER_BASE_URL || "http://127.0.0.1:5000";
const outputDir = path.resolve(__dirname, "..", "artifacts", "baby-intake-checkin");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function assertNoOverflow(page, label) {
  const measurement = await page.evaluate(() => ({
    viewport: innerWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  assert(measurement.document <= measurement.viewport, `${label}: document overflow ${JSON.stringify(measurement)}`);
  assert(measurement.body <= measurement.viewport, `${label}: body overflow ${JSON.stringify(measurement)}`);
}

async function answerFirst(page, questionId) {
  const question = page.locator(`[data-question-id="${questionId}"]`);
  await question.waitFor({ state: "visible" });
  await question.locator("[data-choice-value]").first().click();
}

async function reachSound(page) {
  await page.goto(`${baseUrl}/baby#baby-intake-form`, { waitUntil: "networkidle", timeout: 90000 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const id of ["gender", "style", "familiarity_preference", "discovery_style", "timeless_vs_distinctive"]) {
    await answerFirst(page, id);
  }
    await page.locator('[data-question-id="sound"]').waitFor({ state: "visible" });
    await page.waitForTimeout(300);
}

async function captureScenario(browser, name, viewport, verifyNavigation) {
  const context = await browser.newContext({ viewport, serviceWorkers: "block" });
  const page = await context.newPage();
  const screenshot = (step) => page.screenshot({
    path: path.join(outputDir, `${name}-${step}.png`),
    fullPage: true,
  });

  try {
    await reachSound(page);
    await assertNoOverflow(page, `${name} before`);
    const progressBefore = await page.evaluate(() => {
      const bar = document.querySelector("[data-baby-progressbar]");
      return {
        now: bar.getAttribute("aria-valuenow"),
        max: bar.getAttribute("aria-valuemax"),
        width: document.querySelector("[data-baby-progress-fill]").style.width,
        count: document.querySelector("[data-baby-progress-copy]").textContent,
      };
    });
    await screenshot("before-sound");

    await answerFirst(page, "sound");
    const checkIn = page.locator("[data-intake-checkin]");
    await checkIn.waitFor({ state: "visible" });
    assert((await page.locator("[data-intake-checkin]").count()) === 1, "Check-in DOM was duplicated");
    const progressDuring = await page.evaluate(() => {
      const bar = document.querySelector("[data-baby-progressbar]");
      const count = document.querySelector("[data-baby-progress-copy]");
      return {
        now: bar.getAttribute("aria-valuenow"),
        max: bar.getAttribute("aria-valuemax"),
        width: document.querySelector("[data-baby-progress-fill]").style.width,
        countHidden: count.hidden,
      };
    });
    assert(progressDuring.now === progressBefore.now, "Check-in changed aria-valuenow");
    assert(progressDuring.max === progressBefore.max, "Check-in changed aria-valuemax");
    assert(progressDuring.width === progressBefore.width, "Check-in changed progress width");
    assert(progressDuring.countHidden, "Check-in displays a misleading numbered-question label");
    await assertNoOverflow(page, `${name} check-in`);
    await page.waitForTimeout(300);
    await screenshot("checkin");

    await checkIn.locator('[data-checkin-value="mostly"]').click();
    await page.locator('[data-question-id="cultural_context"]').waitFor({ state: "visible" });
    await assertNoOverflow(page, `${name} after`);
    await page.waitForTimeout(300);
    await screenshot("after-cultural-context");

    const formKeys = await page.evaluate(() => [...new FormData(document.querySelector("#baby-intake-form")).keys()]);
    assert(!formKeys.some((key) => key.includes("checkin") || key.includes("midpoint")), "Check-in leaked into form/query data");
    assert((await page.locator('[data-baby-answer-list] [data-edit-answer="midpoint"]').count()) === 0, "Check-in leaked into answer history");

    if (verifyNavigation) {
      await page.locator("[data-checkin-return]").click();
      await checkIn.waitFor({ state: "visible" });
      assert(
        (await checkIn.locator('[data-checkin-value="mostly"]').getAttribute("aria-checked")) === "true",
        "Back navigation did not restore the selected response"
      );
      await checkIn.locator('[data-checkin-value="yes"]').click();
      await page.locator('[data-question-id="cultural_context"]').waitFor({ state: "visible" });
      await page.locator("[data-checkin-return]").click();
      await checkIn.waitFor({ state: "visible" });
      assert(
        (await checkIn.locator('[data-checkin-value="yes"]').getAttribute("aria-checked")) === "true",
        "The yes response did not advance and restore"
      );
      await checkIn.locator('[data-checkin-value="unsure"]').click();
      await page.locator('[data-question-id="cultural_context"]').waitFor({ state: "visible" });
      await page.locator("[data-checkin-return]").click();
      await checkIn.waitFor({ state: "visible" });
      assert(
        (await checkIn.locator('[data-checkin-value="unsure"]').getAttribute("aria-checked")) === "true",
        "The unsure response did not advance and restore"
      );
      await page.locator("[data-checkin-back]").click();
      await page.locator('[data-question-id="sound"]').waitFor({ state: "visible" });
      await answerFirst(page, "sound");
      await page.locator('[data-question-id="cultural_context"]').waitFor({ state: "visible" });
      assert(await checkIn.isHidden(), "Answered check-in unexpectedly reappeared after editing an earlier answer");

      const stored = await page.evaluate(() => sessionStorage.getItem("namengine:intake-checkin:baby:midpoint:v1"));
      assert(JSON.parse(stored).response === "unsure", "Session persistence did not store the stable response key");

      const savedValues = await page.evaluate(() => {
        const ids = ["gender", "style", "familiarity_preference", "discovery_style", "timeless_vs_distinctive", "sound"];
        return Object.fromEntries(ids.map((id) => [id, document.querySelector(`[name="${id}"]`).value]));
      });
      const resumeUrl = new URL(`${baseUrl}/baby`);
      Object.entries(savedValues).forEach(([key, value]) => resumeUrl.searchParams.set(key, value));
      resumeUrl.hash = "baby-intake-form";
      await page.goto(resumeUrl.toString(), { waitUntil: "networkidle", timeout: 90000 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.locator('[data-question-id="cultural_context"]').waitFor({ state: "visible" });
      await page.locator("[data-checkin-return]").click();
      await checkIn.waitFor({ state: "visible" });
      assert(
        (await checkIn.locator('[data-checkin-value="unsure"]').getAttribute("aria-checked")) === "true",
        "Refresh did not restore the selected check-in response"
      );
      await checkIn.locator('[data-checkin-value="unsure"]').click();
      await page.locator('[data-question-id="cultural_context"]').waitFor({ state: "visible" });
      await page.locator('[data-question-id="cultural_context"] [data-baby-skip]').click();
      await page.locator('[data-question-id="family_context"]').waitFor({ state: "visible" });
    }
  } finally {
    await context.close();
  }
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    await captureScenario(browser, "desktop", { width: 1440, height: 1000 }, true);
    await captureScenario(browser, "mobile", { width: 390, height: 844 }, false);
  } finally {
    await browser.close();
  }
  console.log(`Baby intake check-in verified; screenshots saved to ${outputDir}`);
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
