const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const OUT = path.join(__dirname, "qa-artifacts", "bug-fixes-20260819");
fs.mkdirSync(OUT, { recursive: true });

const MOBILE = { width: 390, height: 844, deviceScaleFactor: 2 };

async function shot(page, name) {
  await page.screenshot({ path: path.join(OUT, name + ".png") });
  console.log("captured:", name);
}

(async () => {
  const browser = await chromium.launch();

  // ── Fix 1: Other + Next button on Pet ──────────────────────────────────────
  const m = await browser.newPage();
  await m.setViewportSize(MOBILE);
  await m.goto("http://127.0.0.1:5000/pet", { waitUntil: "networkidle" });
  await m.click(".baby-begin-button");
  await m.waitForTimeout(400);

  // Click Other on pet_type
  await m.locator("[data-pet-question]:not([hidden]) [data-choice-value='Other']").click();
  await m.waitForTimeout(300);
  await shot(m, "01-pet-other-selected-no-next-yet");
  await m.fill("[data-pet-question]:not([hidden]) [data-other-input]", "Bobcat");
  await m.waitForTimeout(200);
  await shot(m, "02-pet-other-bobcat-with-next-button");

  // ── Fix 2: Auto-advance on Dog (optional question after) ──────────────────
  // click Other first, then Next to move forward, then go to q3 (life_stage optional had no auto-advance before)
  await m.locator("[data-pet-question]:not([hidden]) [data-pet-next]").click();
  await m.waitForTimeout(400);
  // Now on pet_color - fill and next
  await m.fill("[data-pet-question]:not([hidden]) input:not(.pet-native-control)", "Tan");
  await m.locator("[data-pet-question]:not([hidden]) [data-pet-next]").click();
  await m.waitForTimeout(400);
  await shot(m, "03-pet-life-stage-required-auto-advances-on-click");
  // Click Young - should auto-advance to gender (optional)
  await m.locator("[data-pet-question]:not([hidden]) [data-choice-value='Young']").click();
  await m.waitForTimeout(500);
  await shot(m, "04-pet-gender-optional-auto-advance-worked");

  // ── Fix 3: Business priority question ─────────────────────────────────────
  const b = await browser.newPage();
  await b.setViewportSize(MOBILE);
  await b.goto("http://127.0.0.1:5000/business", { waitUntil: "networkidle" });
  await b.click(".baby-begin-button");
  await b.waitForTimeout(400);

  // Fill business description and move through to the priority question
  const textarea = b.locator("[data-business-question]:not([hidden]) textarea").first();
  await textarea.fill("Premium home fragrance studio offering curated candles and diffusers.");
  await b.locator("[data-business-question]:not([hidden]) [data-business-next]").click();
  await b.waitForTimeout(400);

  // Skip through questions to get to priority
  for (let i = 0; i < 10; i++) {
    const nextBtn = b.locator("[data-business-question]:not([hidden]) [data-business-next]").first();
    const choiceBtn = b.locator("[data-business-question]:not([hidden]) [data-choice-value]").first();
    // Check if there's a required choice that needs clicking
    const visibleQuestion = await b.locator("[data-business-question]:not([hidden])").first();
    const required = await visibleQuestion.getAttribute("data-required");
    const kind = await visibleQuestion.getAttribute("data-question-kind");
    if (kind === "choice" && required === "true") {
      await choiceBtn.click();
      await b.waitForTimeout(500);
    } else {
      const hasNext = await nextBtn.count();
      if (hasNext > 0) {
        await nextBtn.click();
        await b.waitForTimeout(400);
      } else {
        break;
      }
    }
    // Check if we've reached priority question
    const priorityQ = await b.locator("[data-question-id='priority_focus']:not([hidden])").count();
    if (priorityQ > 0) break;
  }

  // Try to find the priority question
  await b.waitForSelector("[data-question-id='priority_focus']:not([hidden])", { timeout: 3000 }).catch(() => {});
  await shot(b, "05-business-priority-question");

  // Select "Give everything equal weight"
  const balancedBtn = b.locator("[data-question-id='priority_focus'] [data-choice-value='balanced']");
  const balancedCount = await balancedBtn.count();
  if (balancedCount > 0) {
    await balancedBtn.click();
    await b.waitForTimeout(500);
    await b.waitForSelector("[data-business-direction-review]:not([hidden])", { timeout: 3000 }).catch(() => {});
    await shot(b, "06-business-direction-review-after-priority");
  }

  await browser.close();
  console.log("Done:", OUT);
})().catch(e => { console.error(e); process.exit(1); });
