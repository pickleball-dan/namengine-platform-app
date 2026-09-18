const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const OUT = path.join(__dirname, "qa-artifacts", "pet-guided-review-20260819");
fs.mkdirSync(OUT, { recursive: true });

const MOBILE = { width: 390, height: 844, deviceScaleFactor: 2 };
const DESKTOP = { width: 1024, height: 768, deviceScaleFactor: 1 };

async function shot(page, name) {
  await page.screenshot({ path: path.join(OUT, name + ".png"), fullPage: false });
  console.log("captured:", name);
}

// Click Next on whichever question is currently visible/active
async function clickNext(page) {
  await page.locator("[data-pet-question]:not([hidden]) [data-pet-next]").click({ timeout: 5000 });
  await page.waitForTimeout(400);
}

// Click a choice card in the currently active question
async function clickChoice(page, value) {
  await page.locator(`[data-pet-question]:not([hidden]) [data-choice-value="${value}"]`).click({ timeout: 5000 });
  await page.waitForTimeout(500);
}

// Fill the text/textarea input in the currently active question
async function fillActive(page, value) {
  const input = page.locator("[data-pet-question]:not([hidden]) :is(input:not(.pet-native-control), textarea)").first();
  await input.fill(value, { timeout: 5000 });
  await page.waitForTimeout(200);
}

(async () => {
  const browser = await chromium.launch();

  // ── Mobile ──────────────────────────────────────────────────────────────
  const m = await browser.newPage();
  await m.setViewportSize(MOBILE);
  await m.goto("http://127.0.0.1:5000/pet", { waitUntil: "networkidle" });
  await shot(m, "01-pet-landing-mobile");

  // Start interview
  await m.click(".baby-begin-button");
  await m.waitForTimeout(400);
  await shot(m, "02-pet-q1-who-joins-family");

  // Q1: pet_type — required choice, auto-advance on Dog
  await clickChoice(m, "Dog");
  await shot(m, "03-pet-q2-color-markings");

  // Q2: pet_color — required text
  await fillActive(m, "Golden honey");
  await shot(m, "04-pet-q2-color-filled");
  await clickNext(m);
  await shot(m, "05-pet-q3-young-or-mature");

  // Q3: pet_life_stage — required choice, auto-advance on Young
  await clickChoice(m, "Young");
  await shot(m, "06-pet-q4-gender-optional");

  // Q4: pet_gender — optional choice, tap Next without selecting
  await clickNext(m);
  await shot(m, "07-pet-q5-breed-optional");

  // Q5: pet_breed — optional text, fill and Next
  await fillActive(m, "Golden retriever");
  await clickNext(m);
  await shot(m, "08-pet-q6-details-optional");

  // Q6: pet_details — optional textarea, fill and Next
  await fillActive(m, "Very energetic, loves water, great with kids");
  await clickNext(m);
  await shot(m, "09-pet-q7-vibe");

  // Q7: vibe — required choice, Playful
  await clickChoice(m, "Playful");
  await shot(m, "10-pet-q8-style");

  // Q8: style — required choice, Classic
  await clickChoice(m, "Classic");
  await shot(m, "11-pet-q9-familiarity-optional");

  // Q9: familiarity_preference — optional, skip
  await clickNext(m);
  await shot(m, "12-pet-q10-cultural-context-optional");

  // Q10: cultural_context — optional, skip
  await clickNext(m);
  await shot(m, "13-pet-q11-pronunciation-optional");

  // Q11: pronunciation_importance — optional, skip
  await clickNext(m);
  await shot(m, "14-pet-q12-avoid-optional");

  // Q12: avoid — optional text, skip
  await clickNext(m);

  // ── Your direction review ─────────────────────────────────────────────
  await m.waitForSelector("[data-pet-direction-review]:not([hidden])", { timeout: 4000 }).catch(() => {});
  await m.waitForTimeout(300);
  await shot(m, "15-pet-your-direction-review");

  // ── Desktop first question ────────────────────────────────────────────
  const d = await browser.newPage();
  await d.setViewportSize(DESKTOP);
  await d.goto("http://127.0.0.1:5000/pet", { waitUntil: "networkidle" });
  await shot(d, "16-pet-landing-desktop");
  await d.click(".baby-begin-button");
  await d.waitForTimeout(400);
  await shot(d, "17-pet-q1-desktop");
  await clickChoice(d, "Dog");
  await shot(d, "18-pet-q2-desktop");

  // ── Baby: confirm it is completely unchanged ──────────────────────────
  const b = await browser.newPage();
  await b.setViewportSize(MOBILE);
  await b.goto("http://127.0.0.1:5000/baby", { waitUntil: "networkidle" });
  await b.click(".baby-begin-button");
  await b.waitForTimeout(400);
  await shot(b, "19-baby-unchanged-control");

  await browser.close();

  // HTML review
  const shots = fs.readdirSync(OUT).filter(f => f.endsWith(".png")).sort();
  const html = `<!DOCTYPE html>
<html>
<head><title>Pet Guided Flow Review</title>
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
<h1>Pet Guided Flow — Local Review 2026-08-19</h1>
<p class="meta">Baby is completely untouched. Viewport-cropped screenshots only.</p>
<div class="grid">
${shots.map(f=>`<div class="card"><img src="${f}" alt="${f}"><div class="label">${f}</div></div>`).join("\n")}
</div>
</body></html>`;
  fs.writeFileSync(path.join(OUT, "review.html"), html);
  console.log("\nDone. Review at:", path.join(OUT, "review.html"));
})().catch(e => { console.error(e); process.exit(1); });
