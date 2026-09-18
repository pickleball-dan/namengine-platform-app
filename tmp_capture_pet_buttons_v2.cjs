const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const OUT = path.join(__dirname, "qa-artifacts", "pet-buttons-v2-20260819");
fs.mkdirSync(OUT, { recursive: true });

const MOBILE = { width: 390, height: 844, deviceScaleFactor: 2 };

(async () => {
  const browser = await chromium.launch();
  const m = await browser.newPage();
  await m.setViewportSize(MOBILE);
  await m.goto("http://127.0.0.1:5000/pet", { waitUntil: "networkidle" });

  // Start interview
  await m.click(".baby-begin-button");
  await m.waitForTimeout(500);
  await m.screenshot({ path: path.join(OUT, "01-q1-required-choice-back-next.png") });
  console.log("01 captured");

  // Select Dog (required, auto-advance to color/markings)
  await m.locator("[data-pet-question]:not([hidden]) [data-choice-value='Dog']").click();
  await m.waitForTimeout(500);
  await m.screenshot({ path: path.join(OUT, "02-q2-required-text-next-button.png") });
  console.log("02 captured");

  // Fill color
  await m.locator("[data-pet-question]:not([hidden]) input:not(.pet-native-control)").fill("Golden honey");
  await m.waitForTimeout(200);
  await m.screenshot({ path: path.join(OUT, "03-q2-filled-next-prominent.png") });
  console.log("03 captured");

  // Next → life stage
  await m.locator("[data-pet-question]:not([hidden]) [data-pet-next]").click();
  await m.waitForTimeout(400);

  // Select Young → gender (optional, has Next button)
  await m.locator("[data-pet-question]:not([hidden]) [data-choice-value='Young']").click();
  await m.waitForTimeout(500);
  await m.screenshot({ path: path.join(OUT, "04-optional-choice-both-buttons.png") });
  console.log("04 captured");

  await browser.close();
  console.log("Done →", OUT);
})().catch(e => { console.error(e); process.exit(1); });
