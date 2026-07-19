const { chromium } = require("playwright");

const baseUrl = process.env.NAMENGINE_BROWSER_BASE_URL || "http://127.0.0.1:5000";
const headed = process.env.NAMENGINE_BROWSER_HEADED === "1";
const viewports = [
  { width: 375, height: 667 },
  { width: 390, height: 844 },
  { width: 430, height: 932 },
];
const zooms = [100, 110, 125];
const deviceScaleFactors = [1, 2, 3];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function measure(page) {
  return page.evaluate(() => {
    const rectangle = (element) => {
      const rect = element.getBoundingClientRect();
      return { x: rect.x, right: rect.right, width: rect.width, height: rect.height };
    };
    const details = (selector) => {
      const element = document.querySelector(selector);
      const style = getComputedStyle(element);
      return {
        rectangle: rectangle(element),
        columns: style.gridTemplateColumns,
        transform: style.transform,
      };
    };
    const cards = (selector) =>
      [...document.querySelectorAll(selector)].map((element) => ({
        rectangle: rectangle(element),
        transform: getComputedStyle(element).transform,
      }));

    return {
      viewport: { width: innerWidth, height: innerHeight },
      visualViewport: {
        width: window.visualViewport?.width,
        scale: window.visualViewport?.scale,
      },
      documentClientWidth: document.documentElement.clientWidth,
      devicePixelRatio,
      documentWidth: document.documentElement.scrollWidth,
      main: rectangle(document.querySelector("main")),
      hero: details(".home-hero"),
      heroCopy: details(".home-hero-copy"),
      verticalSection: details(".home-visual-panel"),
      verticalGrid: details(".home-signal-stack"),
      verticalCards: cards(".home-signal-stack > .home-signal-card"),
      legacyVerticalCount: document.querySelectorAll(".home-verticals, .home-vertical-grid, .home-vertical-card").length,
      internalSystemCount: document.querySelectorAll(".home-system-panel").length,
      proofPillCount: document.querySelectorAll(".home-proof-strip span").length,
      viewportMeta: document.querySelector('meta[name="viewport"]')?.content,
      cssHref: document.querySelector('link[href*="platform.css"]')?.href,
    };
  });
}

async function verifyCtaDestinations(browser) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    serviceWorkers: "block",
  });
  const page = await context.newPage();

  try {
    await page.goto(`${baseUrl}/?cta-test=${Date.now()}`, {
      waitUntil: "networkidle",
      timeout: 90000,
    });
    const primary = page.getByRole("link", { name: "Start Baby Naming" });
    const explore = page.getByRole("link", { name: "Explore all naming experiences" });
    assert((await primary.count()) === 0, "Removed Baby CTA still appears");
    assert((await explore.getAttribute("href")) === "#engine-options", "Explore CTA has the wrong destination");
    assert((await page.locator(".home-proof-strip").count()) === 0, "Noninteractive proof pills remain");

    await explore.click();
    await page.waitForFunction(() => window.location.hash === "#engine-options");
    const verticalTop = await page.locator("#engine-options").evaluate((element) => element.getBoundingClientRect().top);
    assert(verticalTop >= -2 && verticalTop < 844, "Explore CTA did not reveal the options cards");
  } finally {
    await context.close();
  }
}

async function run() {
  const browser = await chromium.launch({
    headless: !headed,
    args: headed ? ["--window-position=-2400,-2400"] : [],
  });
  const results = [];

  try {
    await verifyCtaDestinations(browser);
    for (const viewport of viewports) {
      for (const deviceScaleFactor of deviceScaleFactors) {
        for (const zoom of zooms) {
          const context = await browser.newContext({
            viewport,
            deviceScaleFactor,
            serviceWorkers: "block",
          });
          const page = await context.newPage();
          const devtools = await context.newCDPSession(page);
          await devtools.send("Network.enable");
          await devtools.send("Network.setCacheDisabled", { cacheDisabled: true });
          await page.goto(`${baseUrl}/?layout-test=${Date.now()}`, {
            waitUntil: "networkidle",
            timeout: 90000,
          });
          await page.reload({ waitUntil: "networkidle", timeout: 90000 });

          await devtools.send("Emulation.setPageScaleFactor", {
            pageScaleFactor: zoom / 100,
          });

          await page.locator("#engine-options").scrollIntoViewIfNeeded();
          await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
          const measurement = await measure(page);
          const registrations = await page.evaluate(async () =>
            "serviceWorker" in navigator
              ? (await navigator.serviceWorker.getRegistrations()).map((item) => item.scope)
              : []
          );

          // The mobile main container has 14px inline padding on each side.
          // clientWidth excludes the headed browser's scrollbar, so this is
          // the real available content width at every zoom/DPR combination.
          const expectedHeroWidth = measurement.documentClientWidth - 28 - 1;
          // The cleaned homepage nests the CTA and option cards inside padded
          // hero/panel containers, so inner content should be measured against
          // the available padded content width rather than the outer main width.
          const expectedHeroContentWidth = expectedHeroWidth - 32 - 1;
          const expectedCardWidth = expectedHeroContentWidth - 34;
          const allCards = measurement.verticalCards;
          assert(measurement.viewportMeta === "width=device-width, initial-scale=1", "Incorrect viewport meta tag");
          assert(
            Math.abs(measurement.visualViewport.scale - zoom / 100) < 0.01,
            `Browser zoom did not reach ${zoom}%`
          );
          assert(measurement.cssHref.includes("homepage-header-scale-cleanup-v1"), "Stale CSS cache key");
          assert(registrations.length === 0, "Unexpected service worker registration");
          assert(measurement.documentWidth <= measurement.viewport.width, "Horizontal document overflow");
          assert(measurement.hero.rectangle.width >= expectedHeroWidth, "Hero wrapper is compressed");
          assert(measurement.heroCopy.rectangle.width >= expectedHeroContentWidth, "Hero copy is compressed");
          assert(measurement.hero.columns.split(" ").length === 1, "Hero is not one column");
          assert(measurement.legacyVerticalCount === 0, "Legacy vertical card layout remains visible");
          assert(measurement.internalSystemCount === 0, "Internal shared-system section remains visible");
          assert(measurement.proofPillCount === 0, "Noninteractive proof pills remain");
          assert(measurement.verticalSection.rectangle.width >= expectedHeroContentWidth, "Options section is compressed");
          assert(measurement.verticalGrid.columns.split(" ").length === 1, "Options grid is not one column");
          assert(allCards.length === 3, "Expected three options cards");
          assert(allCards.every((card) => card.rectangle.width >= expectedCardWidth), "An options card is compressed");
          assert(allCards.every((card) => card.transform === "none"), "An options card is transformed");

          results.push({ viewport, deviceScaleFactor, zoom, measurement });
          await context.close();
        }
      }
    }
  } finally {
    await browser.close();
  }

  console.log(`Verified ${results.length} homepage mobile layout combinations.`);
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
