'use strict';
/**
 * taste-history.spec.js
 * Playwright tests protecting the loved-name recall chain:
 *   reaction → localStorage → panel renders on return → dialog
 *
 * All tests run locally via: BASE_URL=http://localhost:5000 npx playwright test taste-history
 */
const path = require('path');
const { test, expect } = require('@playwright/test');

// ─── Seed data ────────────────────────────────────────────────────────────────

const SEEDS = {
  baby: {
    key: 'namengine.baby.tasteHistory.v1',
    data: [
      {
        sessionId: 'baby-620e7c9afc86',
        title: 'Baby Round 1',
        context: '8 names · 6 direction selections',
        listUrl: '/results/session/baby-620e7c9afc86',
        shareUrl: '/share/baby-620e7c9afc86',
        lovedNames: ['Elowen', 'Saoirse', 'Niamh'],
        savedAt: '2026-09-01T10:00:00.000Z',
      },
    ],
  },
  pet: {
    key: 'namengine.pet.tasteHistory.v1',
    data: [
      {
        sessionId: 'pet-0275b847cbed',
        title: 'Pet Round 1',
        context: '8 names · 5 direction selections',
        listUrl: '/results/session/pet-0275b847cbed',
        shareUrl: '/share/pet-0275b847cbed',
        lovedNames: ['Calantha', 'Liora', 'Nimue', 'Calithia', 'Neralia'],
        savedAt: '2026-09-01T10:00:00.000Z',
      },
    ],
  },
  business: {
    key: 'namengine.business.tasteHistory.v1',
    data: [
      {
        sessionId: 'business-4b3f47d6ea31',
        title: 'Business Round 1',
        context: '8 names · 7 direction selections',
        listUrl: '/results/session/business-4b3f47d6ea31',
        shareUrl: '/share/business-4b3f47d6ea31',
        lovedNames: ['Northmark', 'Veritas', 'Crestline'],
        savedAt: '2026-09-01T10:00:00.000Z',
      },
    ],
  },
};

async function seedAll(page) {
  await page.evaluate((seeds) => {
    for (const [, seed] of Object.entries(seeds)) {
      window.localStorage.setItem(seed.key, JSON.stringify(seed.data));
    }
  }, SEEDS);
}

async function clearAll(page) {
  await page.evaluate((seeds) => {
    for (const [, seed] of Object.entries(seeds)) {
      window.localStorage.removeItem(seed.key);
    }
  }, SEEDS);
}

// ─── 1. Taste panel: localStorage → UI rendering ──────────────────────────────

test.describe('Taste history panel — localStorage → UI', () => {
  for (const [vertical, seed] of Object.entries(SEEDS)) {
    test(`${vertical} — panel renders loved names from localStorage`, async ({ page }) => {
      // Visit page, seed, reload so taste-history.js picks up fresh data
      await page.goto(`/${vertical}`);
      await page.evaluate(({ key, data }) => {
        window.localStorage.setItem(key, JSON.stringify(data));
      }, seed);
      await page.reload();

      const panel = page.locator('.taste-history-panel');
      await expect(panel).toBeVisible();

      // Each loved name should appear in the panel list
      for (const name of seed.data[0].lovedNames.slice(0, 5)) {
        await expect(panel.locator('[data-taste-history-list]').getByText(name)).toBeVisible();
      }
    });

    test(`${vertical} — panel shows empty-state copy without history`, async ({ page }) => {
      await page.goto(`/${vertical}`);
      await page.evaluate((key) => window.localStorage.removeItem(key), seed.key);
      await page.reload();

      const panel = page.locator('.taste-history-panel');
      await expect(panel).toBeVisible();

      const list = panel.locator('[data-taste-history-list]');
      const firstItem = list.locator('li').first();
      // Should show "Names you love will appear here." (or vertical equivalent)
      await expect(firstItem).not.toBeEmpty();
      await expect(panel.getByText(/appear here/i)).toBeVisible();
    });
  }
});

// ─── 2. NamEngineTasteHistory global is exposed ───────────────────────────────

test.describe('NamEngineTasteHistory global — intake page', () => {
  for (const vertical of ['pet', 'baby', 'business']) {
    test(`${vertical} — exposes NamEngineTasteHistory with add()`, async ({ page }) => {
      await page.goto(`/${vertical}`);

      const type = await page.evaluate(() => typeof window.NamEngineTasteHistory);
      expect(type).toBe('object');

      const hasAdd = await page.evaluate(
        () => typeof window.NamEngineTasteHistory.add === 'function'
      );
      expect(hasAdd).toBe(true);

      const hasRender = await page.evaluate(
        () => typeof window.NamEngineTasteHistory.render === 'function'
      );
      expect(hasRender).toBe(true);
    });
  }
});

// ─── 3. add() writes to localStorage and re-renders the panel ─────────────────

test.describe('NamEngineTasteHistory.add() — localStorage + panel update', () => {
  for (const [vertical, seed] of Object.entries(SEEDS)) {
    test(`${vertical} — add() writes name to localStorage and panel re-renders`, async ({ page }) => {
      await page.goto(`/${vertical}`);

      const testName = `Specname_${vertical}_${Date.now()}`;

      await page.evaluate((name) => {
        window.NamEngineTasteHistory.add(name, 'Loved from results');
      }, testName);

      // Verify localStorage was updated
      const stored = await page.evaluate((key) => {
        const raw = window.localStorage.getItem(key);
        return raw ? JSON.parse(raw) : null;
      }, seed.key);

      expect(stored).not.toBeNull();
      const allLoved = stored.flatMap((s) => s.lovedNames || []);
      expect(allLoved).toContain(testName);

      // Panel should now show the name
      const panel = page.locator('.taste-history-panel');
      await expect(panel.locator('[data-taste-history-list]').getByText(testName)).toBeVisible();
    });
  }
});

// ─── 4. "Review favorites" dialog ─────────────────────────────────────────────

test.describe('Review favorites dialog', () => {
  for (const [vertical, seed] of Object.entries(SEEDS)) {
    test(`${vertical} — dialog opens and shows sessions + Resume link`, async ({ page }) => {
      await page.goto(`/${vertical}`);
      await page.evaluate(({ key, data }) => {
        window.localStorage.setItem(key, JSON.stringify(data));
      }, seed);
      await page.reload();

      const openBtn = page.locator('[data-taste-history-open]');
      await expect(openBtn).toBeVisible();
      await openBtn.click();

      const dialog = page.locator('[data-taste-history-dialog]');
      await expect(dialog).toBeVisible();

      // Should show loved names
      for (const name of seed.data[0].lovedNames.slice(0, 3)) {
        await expect(dialog.getByText(name, { exact: false })).toBeVisible();
      }

      // Should have a Resume link pointing to the right session
      const resumeLink = dialog.locator('a').filter({ hasText: 'Resume' }).first();
      await expect(resumeLink).toBeVisible();
      const href = await resumeLink.getAttribute('href');
      expect(href).toContain(seed.data[0].sessionId);
    });

    test(`${vertical} — dialog can be closed`, async ({ page }) => {
      await page.goto(`/${vertical}`);
      await page.evaluate(({ key, data }) => {
        window.localStorage.setItem(key, JSON.stringify(data));
      }, seed);
      await page.reload();

      await page.locator('[data-taste-history-open]').click();
      const dialog = page.locator('[data-taste-history-dialog]');
      await expect(dialog).toBeVisible();

      await page.locator('[data-taste-history-close]').click();
      await expect(dialog).toBeHidden();
    });
  }
});

// ─── 5. Homepage return hook ───────────────────────────────────────────────────

test.describe('Homepage return hook (homepage-return.js)', () => {
  const SCRIPT_PATH = path.resolve(__dirname, '../../static/js/homepage-return.js');

  test('renders "Pick up where you left off" when all verticals have history', async ({ page }) => {
    await page.goto('/');
    await seedAll(page);
    await page.addScriptTag({ path: SCRIPT_PATH });
    await page.waitForTimeout(300);

    const hook = page.locator('#homepage-return-hook');
    await expect(hook).toBeVisible();

    // Each vertical's loved names should appear
    await expect(hook.getByText('Elowen', { exact: false })).toBeVisible();
    await expect(hook.getByText('Calantha', { exact: false })).toBeVisible();
    await expect(hook.getByText('Northmark', { exact: false })).toBeVisible();

    // Should have Resume links for each
    const resumeLinks = hook.locator('.hpr-resume');
    await expect(resumeLinks).toHaveCount(3);
  });

  test('renders for just one vertical when only that has history', async ({ page }) => {
    await page.goto('/');
    await clearAll(page);
    await page.evaluate(({ key, data }) => {
      window.localStorage.setItem(key, JSON.stringify(data));
    }, SEEDS.pet);
    await page.addScriptTag({ path: SCRIPT_PATH });
    await page.waitForTimeout(300);

    const hook = page.locator('#homepage-return-hook');
    await expect(hook).toBeVisible();

    // Only pet names visible
    await expect(hook.getByText('Calantha', { exact: false })).toBeVisible();
    await expect(hook.locator('.hpr-resume')).toHaveCount(1);
  });

  test('is hidden when localStorage has no history', async ({ page }) => {
    await page.goto('/');
    await clearAll(page);
    await page.addScriptTag({ path: SCRIPT_PATH });
    await page.waitForTimeout(300);

    // Either does not exist or is hidden
    const hook = page.locator('#homepage-return-hook');
    const count = await hook.count();
    if (count > 0) {
      await expect(hook).toBeHidden();
    }
    // If count === 0 the container wasn't created at all — also correct
  });

  test('"Welcome back" heading is visible when history exists', async ({ page }) => {
    await page.goto('/');
    await seedAll(page);
    await page.addScriptTag({ path: SCRIPT_PATH });
    await page.waitForTimeout(300);

    await expect(page.getByText('Pick up where you left off')).toBeVisible();
    await expect(page.getByText(/welcome back/i)).toBeVisible();
  });

  test('Resume links point to correct session URLs', async ({ page }) => {
    await page.goto('/');
    await seedAll(page);
    await page.addScriptTag({ path: SCRIPT_PATH });
    await page.waitForTimeout(300);

    const hook = page.locator('#homepage-return-hook');
    const hrefs = await hook.locator('.hpr-resume').evaluateAll(
      (links) => links.map((a) => a.getAttribute('href'))
    );

    expect(hrefs).toContain('/results/session/baby-620e7c9afc86');
    expect(hrefs).toContain('/results/session/pet-0275b847cbed');
    expect(hrefs).toContain('/results/session/business-4b3f47d6ea31');
  });
});
