const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = process.env.NAMENGINE_BROWSER_BASE_URL || "http://127.0.0.1:5007";
const outputRoot = path.resolve(__dirname, "..", "artifacts", "baby-decision-support", "final");
const viewports = [
  { width: 1440, height: 900, group: "desktop" },
  { width: 768, height: 1024, group: "tablet" },
  { width: 390, height: 844, group: "mobile" },
];
const states = [
  { label: "first-round", url: "/baby/name/baby-decision-first/baby-1", rich: true, learning: false },
  { label: "reacted-eleanor", url: "/baby/name/baby-decision-reacted/baby-1", rich: true, learning: true },
  { label: "reacted-lillian", url: "/baby/name/baby-decision-reacted/baby-2", rich: true, learning: true },
  { label: "reacted-beatrice", url: "/baby/name/baby-decision-reacted/baby-3", rich: true, learning: true },
  { label: "sparse-legacy", url: "/baby/name/baby-decision-sparse/baby-1", rich: false, learning: false },
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function layout(page, label) {
  const report = await page.evaluate(() => {
    const controls = [...document.querySelectorAll("button, a, summary")].filter((element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden";
    });
    return {
      viewport: innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      clipped: controls.filter((element) => {
        const rect = element.getBoundingClientRect();
        return rect.left < -1 || rect.right > innerWidth + 1;
      }).map((element) => element.textContent.trim()),
    };
  });
  assert(report.documentWidth <= report.viewport, `${label}: horizontal overflow ${JSON.stringify(report)}`);
  assert(report.clipped.length === 0, `${label}: clipped controls ${JSON.stringify(report.clipped)}`);
}

(async () => {
  fs.mkdirSync(outputRoot, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of viewports) {
      const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
      const page = await context.newPage();
      for (const state of states) {
        await page.goto(`${baseUrl}${state.url}`, { waitUntil: "networkidle" });
        assert(await page.locator("h1").count() === 1, `${state.label}: missing name heading`);
        assert(await page.getByText("Next decision", { exact: true }).count() === 1, `${state.label}: missing next decision`);
        assert(await page.getByRole("button", { name: "Love this name", exact: true }).count() === 2, `${state.label}: Love controls missing`);
        assert(await page.getByRole("button", { name: "Keep as a maybe", exact: true }).count() === 2, `${state.label}: Maybe controls missing`);
        assert(await page.getByRole("button", { name: "Not for us", exact: true }).count() === 2, `${state.label}: No controls missing`);
        assert(await page.locator("text=quality_score").count() === 0, `${state.label}: exposed internal score`);
        assert(await page.locator("text=Popularity may be increasing").count() === 0, `${state.label}: unsupported popularity claim`);
        if (state.rich) {
          assert(await page.getByText("Why this made your list", { exact: true }).count() === 1, `${state.label}: missing personalized reason`);
          assert(await page.getByText("How it may feel in real life", { exact: true }).count() === 1, `${state.label}: missing real-life section`);
        } else {
          assert(await page.getByText("Why this made your list", { exact: true }).count() === 0, `${state.label}: sparse result showed weak reason`);
          assert(await page.getByText("How it may feel in real life", { exact: true }).count() === 0, `${state.label}: sparse result showed invented real-life copy`);
        }
        assert((await page.getByText("What NamEngine is learning", { exact: true }).count() > 0) === state.learning, `${state.label}: learning visibility mismatch`);
        await layout(page, `${viewport.group}/${state.label}`);
        const directory = path.join(outputRoot, viewport.group, `${viewport.width}x${viewport.height}`);
        fs.mkdirSync(directory, { recursive: true });
        await page.screenshot({ path: path.join(directory, `${state.label}.png`), fullPage: true });
      }

      if (viewport.group === "desktop") {
        await page.goto(`${baseUrl}/baby/name/baby-decision-reacted/baby-1`, { waitUntil: "networkidle" });
        await page.locator('[data-reaction-location="hero"] [data-reaction-value="maybe"]').click();
        await page.waitForFunction(() => [...document.querySelectorAll('[data-reaction-value="maybe"]')].every((button) => button.getAttribute("aria-pressed") === "true"));
        await page.locator('[data-reaction-location="hero"] [data-reaction-value="love"]').click();
        await page.waitForFunction(() => [...document.querySelectorAll('[data-reaction-value="love"]')].every((button) => button.getAttribute("aria-pressed") === "true"));
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }
  console.log(`Baby decision-support screenshots: ${outputRoot}`);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
