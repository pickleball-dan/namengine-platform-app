const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = process.env.NAMENGINE_BROWSER_BASE_URL || "http://127.0.0.1:5005";
const unavailableBaseUrl = process.env.NAMENGINE_UNAVAILABLE_BASE_URL || "http://127.0.0.1:5002";
const sessionId = process.env.NAMENGINE_BABY_RESULTS_SESSION || "baby-acd975f031be";
const chosenId = process.env.NAMENGINE_BABY_CHOSEN_ID || "chosen-97274202c7d7";
const outputRoot = path.resolve(__dirname, "..", "artifacts", "baby-results-polish-v2", "final");

const viewports = [
  { width: 1440, height: 900, group: "wide-desktop" },
  { width: 1280, height: 800, group: "desktop" },
  { width: 1024, height: 768, group: "tablet-landscape" },
  { width: 768, height: 1024, group: "tablet-portrait" },
  { width: 430, height: 932, group: "large-mobile" },
  { width: 360, height: 800, group: "small-mobile" },
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function assertLayout(page, label) {
  const result = await page.evaluate(() => {
    const interactive = [...document.querySelectorAll("button, a, input, textarea, summary")]
      .filter((element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
      });
    return {
      viewport: innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      bodyWidth: document.body.scrollWidth,
      clipped: interactive.filter((element) => {
        const rect = element.getBoundingClientRect();
        return rect.left < -1 || rect.right > innerWidth + 1;
      }).map((element) => element.outerHTML.slice(0, 100)),
    };
  });
  assert(result.documentWidth <= result.viewport, `${label}: document overflow ${JSON.stringify(result)}`);
  assert(result.bodyWidth <= result.viewport, `${label}: body overflow ${JSON.stringify(result)}`);
  assert(result.clipped.length === 0, `${label}: clipped controls ${JSON.stringify(result.clipped)}`);
}

async function capture(page, directory, name) {
  await page.waitForLoadState("networkidle");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await assertLayout(page, name);
  await page.screenshot({ path: path.join(directory, `${name}.png`), fullPage: true });
}

async function assertKeyboardFocus(page, selector, label) {
  for (let index = 0; index < 40; index += 1) {
    await page.keyboard.press("Tab");
    const matched = await page.evaluate((target) => document.activeElement?.matches(target), selector);
    if (matched) {
      const focusStyle = await page.evaluate(() => {
        const style = getComputedStyle(document.activeElement);
        return { outline: style.outlineStyle, shadow: style.boxShadow };
      });
      assert(
        focusStyle.outline !== "none" || focusStyle.shadow !== "none",
        `${label}: keyboard focus is not visibly styled`
      );
      return;
    }
  }
  throw new Error(`${label}: keyboard navigation could not reach ${selector}`);
}

async function runViewport(browser, viewport) {
  const context = await browser.newContext({ viewport, serviceWorkers: "block" });
  const page = await context.newPage();
  const directory = path.join(outputRoot, viewport.group, `${viewport.width}x${viewport.height}`);
  fs.mkdirSync(directory, { recursive: true });

  try {
    await page.goto(`${baseUrl}/baby`);
    await capture(page, directory, "01-entry");

    await page.goto(`${baseUrl}/baby?edit=cultural_context#baby-intake-form`);
    await page.locator('[data-question-id="cultural_context"]').waitFor({ state: "visible" });
    assert(await page.locator('[data-choice-value="Family heritage"]').count() === 0, "Family heritage card is visible");
    const legacyControl = page.locator('#cultural_heritage');
    assert(await legacyControl.getAttribute("tabindex") === "-1", "Legacy heritage control can receive keyboard focus");
    assert(await legacyControl.getAttribute("aria-hidden") === "true", "Legacy heritage control is exposed to assistive technology");
    assert(await page.locator('[data-question-id="cultural_heritage"]').isHidden(), "Legacy heritage question is reachable in the normal UI");
    await assertKeyboardFocus(page, '[data-question-id="cultural_context"] [data-choice-value]', "Name inspiration");
    await capture(page, directory, "02-name-inspiration");

    await page.goto(`${baseUrl}/baby/feelings?gender=Girl&style=Classic&sound=Soft`);
    await capture(page, directory, "03-feelings");

    let generationRequests = 0;
    page.on("request", (request) => {
      if (request.url().includes("/baby/results")) generationRequests += 1;
    });
    await page.locator("[data-baby-weight]").first().click();
    await page.evaluate(() => document.querySelector("[data-baby-weight]")?.click());
    await page.locator("[data-progress-overlay]").waitFor({ state: "visible" });
    await capture(page, directory, "04-thinking");
    if (viewport.width === 1440) {
      await page.waitForURL(/\/results\/session\/baby-/, { timeout: 15000 });
      assert(generationRequests === 1, `Generation submitted ${generationRequests} times`);
    }

    await page.goto(`${baseUrl}/results/session/${sessionId}`);
    assert(await page.locator('[data-result-card-toggle][aria-expanded="true"]').count() === 0, "Result details should start collapsed");
    const cardCount = await page.locator("[data-result-card]").count();
    assert(await page.locator(".result-explore-link").count() === cardCount, "Every result needs an Explore action");
    assert(await page.locator(".result-name-link").count() === cardCount, "Every result name needs a detail link");
    assert(await page.locator(".result-explore-link").evaluateAll((links) => links.every((link) => link.textContent.trim() === "Explore →")), "Explore labels are inconsistent");
    assert(await page.getByText("Tell me more", { exact: true }).count() === 0, "Legacy learn-more language is still visible");
    assert(await page.getByText(/^Option [4-8]$/i).count() === 0, "Generic option labels are still visible");
    const destinationsMatch = await page.locator("[data-result-card]").evaluateAll((cards) => cards.every((card) => (
      card.querySelector(".result-name-link")?.getAttribute("href") === card.querySelector(".result-explore-link")?.getAttribute("href")
    )));
    assert(destinationsMatch, "A result title and Explore action lead to different destinations");
    const columns = await page.locator("[data-result-card]").evaluateAll((cards) => {
      const top = Math.min(...cards.map((card) => Math.round(card.getBoundingClientRect().top)));
      return cards.filter((card) => Math.abs(Math.round(card.getBoundingClientRect().top) - top) <= 1).length;
    });
    const expectedColumns = viewport.width >= 1180 ? 4 : viewport.width >= 821 ? 3 : 1;
    assert(columns === expectedColumns, `${viewport.width}px rendered ${columns} columns; expected ${expectedColumns}`);
    if (expectedColumns > 1) {
      const alignment = await page.locator("[data-result-card]").evaluateAll((cards, count) => {
        const firstRow = cards.slice(0, count);
        const y = (card, selector) => Math.round(card.querySelector(selector).getBoundingClientRect().top);
        const spread = (values) => Math.max(...values) - Math.min(...values);
        return {
          reactions: spread(firstRow.map((card) => y(card, ".reaction-row"))),
          explore: spread(firstRow.map((card) => y(card, ".result-explore-link"))),
          quickView: spread(firstRow.map((card) => y(card, ".result-card-toggle"))),
        };
      }, expectedColumns);
      assert(alignment.reactions <= 2, `Reaction rows are misaligned: ${JSON.stringify(alignment)}`);
      assert(alignment.explore <= 2, `Explore actions are misaligned: ${JSON.stringify(alignment)}`);
      assert(alignment.quickView <= 2, `Quick-view controls are misaligned: ${JSON.stringify(alignment)}`);
    }
    await capture(page, directory, "05-results");

    const toggles = page.locator("[data-result-card-toggle]");
    await toggles.nth(1).click();
    assert(await page.locator("[data-result-card].is-expanded").count() === 1, "Quick view did not produce one active card");
    await toggles.nth(2).click();
    assert(await page.locator("[data-result-card].is-expanded").count() === 1, "More than one quick view remained expanded");
    assert(await toggles.nth(1).getAttribute("aria-expanded") === "false", "Previous quick view did not close");
    const expandedLayout = await page.locator("[data-result-card].is-expanded").evaluate((card) => {
      const cardRect = card.getBoundingClientRect();
      const detailsRect = card.querySelector("[data-result-card-details]").getBoundingClientRect();
      const style = getComputedStyle(card);
      return {
        contained: detailsRect.left >= cardRect.left && detailsRect.right <= cardRect.right && detailsRect.bottom <= cardRect.bottom + 1,
        zIndex: Number(style.zIndex || 0),
        transform: style.transform,
      };
    });
    assert(expandedLayout.contained, "Expanded content escaped the active card surface");
    assert(expandedLayout.zIndex >= 4, "Expanded card is not elevated in the stacking order");
    if (viewport.width >= 821) assert(expandedLayout.transform !== "none", "Desktop expanded card has no lift treatment");
    await assertLayout(page, `expanded-${viewport.width}`);
    await capture(page, directory, "05b-results-expanded");
    await toggles.nth(2).click();

    const firstLove = page.locator('[data-reaction-value="love"]').first();
    await firstLove.click();
    await page.locator(".reaction-status").first().filter({ hasText: "Saved" }).waitFor();
    assert(await page.locator("[data-saved-count]").textContent().then((text) => /You loved \d+ names? in Round 1\./.test(text)), "Learning count was not acknowledged");
    assert(await page.locator(".baby-saved-progress small").getByText("refine your next recommendations", { exact: false }).count() === 1, "Learning impact is not explained");
    await capture(page, directory, "06-reaction-saved");
    await page.reload({ waitUntil: "networkidle" });
    assert(await page.locator('[data-reaction-value="love"]').first().getAttribute("aria-pressed") === "true", "Reaction did not survive reload");

    await page.goto(`${baseUrl}/baby/name/${sessionId}/baby-1`);
    assert(await page.locator(".baby-secondary-disclosure[open]").count() === 0, "Secondary name details should start collapsed");
    assert(await page.locator(".name-fact-overview[open]").count() === 0, "Name facts should start collapsed");
    assert(await page.locator(".baby-detail-primary").count() === 1, "Why this name fits is not the primary detail section");
    await capture(page, directory, "07-name-detail");

    await page.goto(`${baseUrl}/compare/${sessionId}`);
    assert(await page.locator(".compare-card-details").count() > 0, "Compare progressive disclosure is missing");
    await capture(page, directory, "08-shortlist");

    await page.goto(`${baseUrl}/share/${sessionId}`);
    assert(await page.locator(".shared-result-details").count() > 0, "Shared-list progressive disclosure is missing");
    await capture(page, directory, "09-share");

    await page.goto(`${baseUrl}/chosen/${chosenId}`);
    const chosenHeading = await page.locator("h1").textContent();
    await capture(page, directory, "10-keepsake");
    await page.reload({ waitUntil: "networkidle" });
    assert(await page.locator("h1").textContent() === chosenHeading, "Chosen-name state did not survive reload");

    const missing = await page.goto(`${baseUrl}/share/baby-missing-review`);
    assert(missing.status() === 410, `Expected 410 missing share, got ${missing.status()}`);
    await capture(page, directory, "11-expired-share");

    const unavailable = await page.goto(`${unavailableBaseUrl}/__review/baby-generation-unavailable`);
    assert(unavailable.status() === 503, `Expected unavailable status 503, got ${unavailable.status()}`);
    await capture(page, directory, "12-generation-recovery");
    const reviewOrigin = new URL(baseUrl).origin;
    await Promise.all([
      page.waitForURL((url) => url.origin === reviewOrigin),
      page.getByRole("link", { name: "Go back and try again" }).click(),
    ]);
    assert(page.url().startsWith(baseUrl), `Recovery action stopped at ${page.url()}`);
  } finally {
    await context.close();
  }
}

(async () => {
  fs.mkdirSync(outputRoot, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of viewports) await runViewport(browser, viewport);
  } finally {
    await browser.close();
  }
  console.log(`Baby journey screenshots: ${outputRoot}`);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
