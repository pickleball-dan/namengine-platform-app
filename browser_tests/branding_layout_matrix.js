const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = process.env.NAMENGINE_BROWSER_BASE_URL || "http://127.0.0.1:5000";
const unavailableBaseUrl = process.env.NAMENGINE_UNAVAILABLE_BASE_URL || baseUrl;
const capturePhase = process.env.NAMENGINE_BRANDING_CAPTURE_PHASE || "final";
const outputRoot = path.resolve(__dirname, "..", "artifacts", "branding-layout", capturePhase);
const babyResultsSession = process.env.NAMENGINE_BABY_RESULTS_SESSION || "baby-acd975f031be";

const viewports = [
  { width: 1440, height: 900, group: "desktop" },
  { width: 1280, height: 800, group: "desktop" },
  { width: 1024, height: 768, group: "tablet" },
  { width: 768, height: 1024, group: "tablet" },
  { width: 430, height: 932, group: "mobile" },
  { width: 390, height: 844, group: "mobile" },
  { width: 360, height: 800, group: "mobile" },
];

const intakeOrder = [
  "gender",
  "style",
  "familiarity_preference",
  "discovery_style",
  "timeless_vs_distinctive",
  "sound",
  "cultural_context",
  "family_context",
  "partner_alignment",
  "avoid",
  "notes",
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function safeName(value) {
  return value.replace(/[^a-z0-9-]+/gi, "-").replace(/^-|-$/g, "").toLowerCase();
}

async function inspectLayout(page, label) {
  const metrics = await page.evaluate(() => {
    const rect = (element) => {
      if (!element) return null;
      const value = element.getBoundingClientRect();
      return {
        x: Math.round(value.x * 100) / 100,
        y: Math.round(value.y * 100) / 100,
        width: Math.round(value.width * 100) / 100,
        height: Math.round(value.height * 100) / 100,
        right: Math.round(value.right * 100) / 100,
        bottom: Math.round(value.bottom * 100) / 100,
      };
    };
    const overlaps = (left, right) => left && right
      ? !(left.right <= right.x || right.right <= left.x || left.bottom <= right.y || right.bottom <= left.y)
      : false;
    const header = rect(document.querySelector(".site-header"));
    const headerBrand = rect(document.querySelector(".site-header .brand"));
    const navigation = rect(document.querySelector(".site-header .site-nav"));
    const visibleLogos = [...document.querySelectorAll("img")]
      .filter((image) => {
        const style = getComputedStyle(image);
        const imageRect = image.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && imageRect.width > 0 && imageRect.height > 0;
      })
      .filter((image) => /namengine|favicon|app-icon/i.test(image.currentSrc || image.src))
      .map((image) => ({
        src: image.getAttribute("src"),
        alt: image.getAttribute("alt"),
        naturalWidth: image.naturalWidth,
        naturalHeight: image.naturalHeight,
        rect: rect(image),
        objectFit: getComputedStyle(image).objectFit,
      }));
    const boundarySelectors = [
      ".site-header",
      ".site-header .brand",
      ".site-header .site-nav",
      ".site-footer",
      ".site-footer .footer-brand-block",
      ".site-footer .footer-links",
      ".baby-interview-header",
      ".baby-interview-brand",
      ".baby-question-progress",
      ".baby-final-question",
      ".baby-final-question .baby-choice-list",
      ".vertical-page-logo",
      ".home-brand-lockup",
      ".home-vertical-card",
    ];
    const outOfBounds = boundarySelectors.flatMap((selector) =>
      [...document.querySelectorAll(selector)].flatMap((element) => {
        const style = getComputedStyle(element);
        const value = element.getBoundingClientRect();
        if (style.display === "none" || style.visibility === "hidden" || value.width === 0 || value.height === 0) return [];
        if (value.x >= -0.5 && value.right <= innerWidth + 0.5) return [];
        return [{ selector, rect: rect(element) }];
      })
    );
    return {
      viewport: { width: innerWidth, height: innerHeight },
      documentWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      header,
      headerBrand,
      navigation,
      headerNavigationOverlap: overlaps(headerBrand, navigation),
      visibleLogos,
      outOfBounds,
    };
  });

  assert(metrics.documentWidth <= metrics.viewport.width, `${label}: document overflow ${JSON.stringify(metrics)}`);
  assert(metrics.bodyWidth <= metrics.viewport.width, `${label}: body overflow ${JSON.stringify(metrics)}`);
  assert(!metrics.headerNavigationOverlap, `${label}: header brand overlaps navigation`);
  assert(metrics.outOfBounds.length === 0, `${label}: visible layout exceeds viewport ${JSON.stringify(metrics.outOfBounds)}`);
  for (const logo of metrics.visibleLogos) {
    assert(logo.naturalWidth > 0 && logo.naturalHeight > 0, `${label}: logo did not load ${logo.src}`);
    assert(logo.rect.width > 0 && logo.rect.height > 0, `${label}: logo has no rendered size ${logo.src}`);
  }
  return metrics;
}

async function capture(page, directory, name, records) {
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const label = `${path.basename(directory)} ${name}`;
  const metrics = await inspectLayout(page, label);
  const file = path.join(directory, `${safeName(name)}.png`);
  await page.screenshot({ path: file, fullPage: true });
  records.push({ name, file: path.relative(outputRoot, file), url: page.url(), metrics });
}

async function answerQuestion(page, questionId) {
  const question = page.locator(`[data-question-id="${questionId}"]`);
  if (questionId === "cultural_context") {
    const heritage = question.locator('[data-choice-value="Family heritage"]');
    if (await heritage.count()) {
      await heritage.click();
      return;
    }
  }
  if (["family_context", "partner_alignment", "avoid", "notes"].includes(questionId)) {
    const skip = question.locator("[data-baby-skip]");
    if (await skip.count()) {
      await skip.click();
      return;
    }
    const input = question.locator("input, textarea").first();
    await input.fill("Visual review");
    await question.locator("[data-baby-continue]").click();
    return;
  }
  await question.locator("[data-choice-value]").first().click();
}

async function captureIntake(page, directory, records) {
  await page.goto(`${baseUrl}/baby?branding-layout=${Date.now()}#baby-intake-form`, {
    waitUntil: "networkidle",
    timeout: 90000,
  });
  await page.emulateMedia({ reducedMotion: "reduce" });

  for (const questionId of intakeOrder) {
    if (questionId === "cultural_context") {
      const checkIn = page.locator("[data-intake-checkin]");
      await checkIn.waitFor({ state: "visible" });
      await capture(page, directory, "intake-07-check-in", records);
      await checkIn.locator('[data-checkin-value="mostly"]').click();
    }
    const question = page.locator(`[data-question-id="${questionId}"]`);
    await question.waitFor({ state: "visible" });
    const step = String(intakeOrder.indexOf(questionId) + 1).padStart(2, "0");
    await capture(page, directory, `intake-${step}-${questionId}`, records);
    await answerQuestion(page, questionId);
  }

  await page.waitForURL(/\/baby\/feelings(?:\?|$)/, { timeout: 90000 });
  await capture(page, directory, "feelings-scale-after-intake", records);
}

async function captureViewport(browser, viewport) {
  const directory = path.join(outputRoot, viewport.group, `${viewport.width}x${viewport.height}`);
  fs.mkdirSync(directory, { recursive: true });
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    serviceWorkers: "block",
  });
  const page = await context.newPage();
  const records = [];
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  try {
    await page.goto(`${baseUrl}/?branding-layout=${Date.now()}`, { waitUntil: "networkidle", timeout: 90000 });
    await capture(page, directory, "home", records);

    await page.goto(`${baseUrl}/baby?branding-layout=${Date.now()}`, { waitUntil: "networkidle", timeout: 90000 });
    await capture(page, directory, "baby-welcome", records);

    await captureIntake(page, directory, records);

    await page.goto(
      `${baseUrl}/baby/feelings?gender=Girl&style=Classic&sound=Soft&branding-layout=${Date.now()}`,
      { waitUntil: "networkidle", timeout: 90000 }
    );
    await capture(page, directory, "feelings-scale-direct", records);

    const resultsResponse = await page.goto(`${baseUrl}/results/session/${babyResultsSession}`, {
      waitUntil: "networkidle",
      timeout: 90000,
    });
    if (resultsResponse && resultsResponse.status() === 200) {
      await capture(page, directory, "baby-results", records);
    }

    const unavailableResponse = await page.goto(
      `${unavailableBaseUrl}/__review/baby-generation-unavailable`,
      { waitUntil: "networkidle", timeout: 90000 }
    );
    assert(unavailableResponse && unavailableResponse.status() === 503, "Expected the generation unavailable page");
    await capture(page, directory, "generation-unavailable", records);

    assert(pageErrors.length === 0, `${viewport.width}x${viewport.height}: page errors ${pageErrors.join(" | ")}`);
    fs.writeFileSync(path.join(directory, "metrics.json"), JSON.stringify(records, null, 2));
    return { viewport, screenshots: records.length };
  } finally {
    await context.close();
  }
}

async function run() {
  fs.mkdirSync(outputRoot, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const summary = [];
  try {
    for (const viewport of viewports) {
      summary.push(await captureViewport(browser, viewport));
    }
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(outputRoot, "summary.json"), JSON.stringify(summary, null, 2));
  console.log(`Captured ${summary.reduce((total, item) => total + item.screenshots, 0)} screenshots in ${outputRoot}`);
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
