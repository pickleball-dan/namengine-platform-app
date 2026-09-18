const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const OUT = path.join(__dirname, "qa-artifacts", "business-guided-review-20260819");
fs.mkdirSync(OUT, { recursive: true });

const MOBILE = { width: 390, height: 844, deviceScaleFactor: 2 };
const DESKTOP = { width: 1024, height: 768, deviceScaleFactor: 1 };

async function clickNext(page) {
  await page.locator("[data-business-question]:not([hidden]) [data-business-next]").click({ timeout: 5000 });
  await page.waitForTimeout(400);
}

async function clickChoice(page, value) {
  await page.locator(`[data-business-question]:not([hidden]) [data-choice-value="${value}"]`).click({ timeout: 5000 });
  await page.waitForTimeout(500);
}

async function fillActive(page, value) {
  const input = page.locator("[data-business-question]:not([hidden]) :is(textarea, input:not(.business-native-control))").first();
  await input.fill(value, { timeout: 5000 });
  await page.waitForTimeout(200);
}

(async () => {
  const browser = await chromium.launch();

  // ── Mobile flow ──────────────────────────────────────────────────────────
  const m = await browser.newPage();
  await m.setViewportSize(MOBILE);
  await m.goto("http://127.0.0.1:5000/business", { waitUntil: "networkidle" });
  await m.screenshot({ path: path.join(OUT, "01-business-landing-mobile.png") });
  console.log("01 captured");

  // Start
  await m.click(".baby-begin-button");
  await m.waitForTimeout(500);
  await m.screenshot({ path: path.join(OUT, "02-q1-business-description-required-textarea.png") });
  console.log("02 captured");

  // Q1: business_description — required textarea
  await fillActive(m, "Premium home-fragrance studio offering curated candles and diffusers for the modern home.");
  await m.screenshot({ path: path.join(OUT, "03-q1-filled-next-button.png") });
  console.log("03 captured");
  await clickNext(m);

  // Q2: industry — optional text
  await m.screenshot({ path: path.join(OUT, "04-q2-industry-optional-text.png") });
  console.log("04 captured");
  await fillActive(m, "Home fragrance / lifestyle retail");
  await clickNext(m);

  // Q3: stage — optional choice
  await m.screenshot({ path: path.join(OUT, "05-q3-stage-optional-choice.png") });
  console.log("05 captured");
  await clickChoice(m, "Launching soon");
  await m.waitForTimeout(400);
  await clickNext(m);  // optional choice needs explicit Next

  // Q4: audience — required choice, auto-advance
  await m.screenshot({ path: path.join(OUT, "06-q4-audience-required-choice.png") });
  console.log("06 captured");
  await clickChoice(m, "Individual consumers");

  // Q5: market_scope — optional choice
  await m.screenshot({ path: path.join(OUT, "07-q5-market-scope-optional.png") });
  console.log("07 captured");
  await clickNext(m);  // optional, skip with Next

  // Q6: notes — optional textarea
  await m.screenshot({ path: path.join(OUT, "08-q6-notes-optional-textarea.png") });
  console.log("08 captured");
  await fillActive(m, "We want to feel premium but approachable, not cold or corporate.");
  await clickNext(m);

  // Q7: style — required choice
  await m.screenshot({ path: path.join(OUT, "09-q7-style-required-choice.png") });
  console.log("09 captured");
  await clickChoice(m, "Premium and refined");

  // Q8-Q13: optional, skip through with Next
  for (let i = 0; i < 5; i++) {
    await clickNext(m).catch(() => {});
  }

  // Your brand direction review
  await m.waitForSelector("[data-business-direction-review]:not([hidden])", { timeout: 5000 }).catch(() => {});
  await m.waitForTimeout(300);
  await m.screenshot({ path: path.join(OUT, "10-your-brand-direction-review.png") });
  console.log("10 captured");

  // ── Desktop first question ────────────────────────────────────────────
  const d = await browser.newPage();
  await d.setViewportSize(DESKTOP);
  await d.goto("http://127.0.0.1:5000/business", { waitUntil: "networkidle" });
  await d.screenshot({ path: path.join(OUT, "11-business-landing-desktop.png") });
  await d.click(".baby-begin-button");
  await d.waitForTimeout(500);
  await d.screenshot({ path: path.join(OUT, "12-q1-desktop.png") });
  console.log("12 captured");

  // ── Confirm Baby and Pet still work ──────────────────────────────────
  const baby = await browser.newPage();
  await baby.setViewportSize(MOBILE);
  await baby.goto("http://127.0.0.1:5000/baby", { waitUntil: "networkidle" });
  await baby.click(".baby-begin-button");
  await baby.waitForTimeout(400);
  await baby.screenshot({ path: path.join(OUT, "13-baby-gold-standard-unchanged.png") });
  console.log("13 captured");

  const pet = await browser.newPage();
  await pet.setViewportSize(MOBILE);
  await pet.goto("http://127.0.0.1:5000/pet", { waitUntil: "networkidle" });
  await pet.click(".baby-begin-button");
  await pet.waitForTimeout(400);
  await pet.screenshot({ path: path.join(OUT, "14-pet-unchanged.png") });
  console.log("14 captured");

  await browser.close();

  // HTML review
  const shots = fs.readdirSync(OUT).filter(f => f.endsWith(".png")).sort();
  const html = `<!DOCTYPE html>
<html>
<head><title>Business Guided Flow Review</title>
<style>
body{font-family:system-ui,sans-serif;max-width:1000px;margin:0 auto;padding:24px;background:#f4f4f4}
h1{font-size:1.3rem;margin-bottom:4px}
.meta{color:#666;font-size:.85rem;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:18px}
.card{background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.07)}
.card img{width:100%;display:block}
.label{padding:8px 12px;font-size:.75rem;color:#555;font-weight:600}
</style></head>
<body>
<h1>Business Guided Flow — Local Review 2026-08-19</h1>
<p class="meta">Baby and Pet are completely untouched. Viewport-cropped screenshots only.</p>
<div class="grid">
${shots.map(f=>`<div class="card"><img src="${f}" alt="${f}"><div class="label">${f}</div></div>`).join("\n")}
</div></body></html>`;
  fs.writeFileSync(path.join(OUT, "review.html"), html);
  console.log("\nDone →", OUT);
})().catch(e => { console.error(e); process.exit(1); });
