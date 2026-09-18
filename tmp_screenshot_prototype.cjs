const { chromium } = require("playwright");
const path = require("path");

const FILE = "file:///" + path.resolve("tmp_heritage_search_prototype.html").replace(/\\/g, "/");

async function shot(page, name) {
  await page.screenshot({ path: `tmp_proto_${name}.png`, clip: { x: 0, y: 0, width: 430, height: 750 } });
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  // Mobile viewport
  const page = await browser.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(FILE, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(300);

  // 1. Default state
  await shot(page, "1_default");

  // 2. Typing "iri" — filters to Irish, etc.
  await page.fill("#searchInput", "iri");
  await page.waitForTimeout(200);
  await shot(page, "2_typing_iri");

  // 3. Typing something not in list
  await page.fill("#searchInput", "Sudanese");
  await page.waitForTimeout(200);
  await shot(page, "3_custom_sudanese");

  // 4. Clear + show all
  await page.click("#clearBtn");
  await page.waitForTimeout(150);
  await page.click("#showAllBtn");
  await page.waitForTimeout(200);
  await shot(page, "4_show_all");

  // 5. Select "Irish" and show selected state
  await page.click("#clearBtn").catch(() => {});
  await page.fill("#searchInput", "iri");
  await page.waitForTimeout(200);
  const irishChip = page.locator('.chip[data-value="Irish"]').first();
  await irishChip.click();
  await page.waitForTimeout(200);
  await shot(page, "5_selected_irish");

  // 6. No preference selected
  await page.click("#clearBtn").catch(() => {});
  await page.waitForTimeout(100);
  await page.click("#noPrefBtn");
  await page.waitForTimeout(200);
  await shot(page, "6_no_preference");

  await browser.close();
  console.log("done");
}

run().catch(e => { console.error(e); process.exit(1); });
