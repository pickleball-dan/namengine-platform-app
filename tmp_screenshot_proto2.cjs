const { chromium } = require("playwright");
const BASE = "http://127.0.0.1:5200/static/tmp_heritage_proto.html";

async function shot(p, name, h = 844) {
  await p.screenshot({ path: `tmp_proto_${name}.png`, clip: { x: 0, y: 0, width: 390, height: h } });
}

(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  await p.setViewportSize({ width: 390, height: 844 });
  await p.goto(BASE, { waitUntil: "networkidle" });
  await p.waitForTimeout(600);

  // 1. Default — 12 common heritages
  await shot(p, "1_default");

  // 2. Typing "iri"
  await p.fill("#searchInput", "iri");
  await p.waitForTimeout(200);
  await shot(p, "2_typing_iri");

  // 3. Custom value "Sudanese"
  await p.fill("#searchInput", "Sudanese");
  await p.waitForTimeout(200);
  await shot(p, "3_custom_sudanese");

  // 4. Show all 50
  await p.fill("#searchInput", "");
  await p.click("#showAllBtn");
  await p.waitForTimeout(200);
  await shot(p, "4_show_all");

  // 5. Selected Irish
  await p.fill("#searchInput", "iri");
  await p.waitForTimeout(200);
  const irishBtn = p.locator(".baby-choice").filter({ hasText: "Irish" }).first();
  await irishBtn.click();
  await p.waitForTimeout(200);
  await shot(p, "5_selected_irish");

  await b.close();
  console.log("done");
})().catch(e => { console.error(e); process.exit(1); });
