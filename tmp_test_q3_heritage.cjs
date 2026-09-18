const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  await p.setViewportSize({ width: 390, height: 844 });
  await p.goto("http://127.0.0.1:5200/baby", { waitUntil: "networkidle" });
  await p.click(".baby-begin-button");
  await p.waitForTimeout(500);

  // Q1 gender
  await p.locator("[data-baby-question]:not([hidden]) [data-choice-value]").first().click();
  await p.waitForTimeout(500);
  const q2 = await p.locator("[data-baby-question]:not([hidden])").first().getAttribute("data-question-id");
  console.log("Q2:", q2);

  // Q2 style
  await p.locator("[data-baby-question]:not([hidden]) [data-choice-value]").first().click();
  await p.waitForTimeout(500);
  const q3 = await p.locator("[data-baby-question]:not([hidden])").first().getAttribute("data-question-id");
  console.log("Q3:", q3, q3 === "cultural_heritage" ? "✅" : "❌ expected cultural_heritage");

  // Search UI visible?
  const searchInput = p.locator("[data-heritage-search]");
  const vis = await searchInput.isVisible().catch(() => false);
  console.log("search input visible:", vis ? "✅" : "❌");

  if (vis) {
    await searchInput.fill("Iri");
    await p.waitForTimeout(300);
    await p.screenshot({ path: "tmp_q3_heritage_search.png" });
    console.log("📸 tmp_q3_heritage_search.png");

    const irishBtn = p.locator("[data-heritage-value]").filter({ hasText: "Irish" }).first();
    await irishBtn.waitFor({ state: "visible", timeout: 3000 });
    await irishBtn.click();
    await p.waitForTimeout(700);

    const q4 = await p.locator("[data-baby-question]:not([hidden])").first().getAttribute("data-question-id").catch(() => "review");
    console.log("Q4 after selecting Irish:", q4, q4 === "familiarity_preference" ? "✅" : "(check order)");
  }

  await b.close();
  console.log("done");
})().catch(e => { console.error(e); process.exit(1); });
