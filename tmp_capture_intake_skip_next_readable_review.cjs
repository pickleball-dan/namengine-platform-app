const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:5000';
const OUT = path.join('qa-artifacts', 'intake-text-skip-next-review-readable-20260819-1029');
fs.mkdirSync(OUT, { recursive: true });

async function viewportShot(page, name) {
  const shot = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: shot, fullPage: false });
  return shot;
}

async function showQuestion(page, id) {
  await page.evaluate((questionId) => {
    document.body.classList.add('baby-interview-started');
    document.querySelectorAll('[data-baby-question]').forEach((q) => {
      const active = q.dataset.questionId === questionId;
      q.hidden = !active;
      q.classList.toggle('is-active', active);
    });
    document.querySelector('[data-baby-question-stage]')?.removeAttribute('hidden');
    document.querySelector('[data-baby-complete]')?.setAttribute('hidden', '');
    const q = document.querySelector(`[data-question-id="${questionId}"]`);
    q?.scrollIntoView({ block: 'center' });
    q?.querySelector('textarea, input:not([type="hidden"]):not([data-other-input])')?.focus({ preventScroll: true });
  }, id);
}

async function state(page) {
  return await page.evaluate(() => {
    const q = document.querySelector('[data-baby-question]:not([hidden])');
    const input = q && q.querySelector('textarea, input:not([type="hidden"]):not([data-other-input])');
    const skip = q && q.querySelector('[data-baby-skip]');
    return {
      question: q?.querySelector('h2')?.textContent.trim(),
      questionId: q?.dataset.questionId,
      value: input?.value || '',
      button: skip?.textContent.trim() || q?.querySelector('[data-baby-continue]')?.textContent.trim(),
      actionState: skip?.dataset.actionState || null,
    };
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });
  const report = [];

  await page.goto(`${BASE}/baby`, { waitUntil: 'networkidle' });
  await showQuestion(page, 'family_context');
  report.push({ label: 'Baby empty text field: button remains Skip', state: await state(page), screenshot: await viewportShot(page, '01-baby-empty-skip-readable') });

  await page.locator('[data-question-id="family_context"] textarea, [data-question-id="family_context"] input:not([type="hidden"])').fill('Last name Parker; we like soft classic names.');
  await page.waitForTimeout(100);
  report.push({ label: 'Baby typed text field: button changes to Next', state: await state(page), screenshot: await viewportShot(page, '02-baby-typed-next-readable') });

  await page.keyboard.press('Enter');
  await page.waitForTimeout(350);
  report.push({ label: 'After Enter: moves to next question', state: await state(page), screenshot: await viewportShot(page, '03-baby-after-enter-readable') });

  for (const vertical of ['pet', 'business']) {
    await page.goto(`${BASE}/${vertical}`, { waitUntil: 'networkidle' });
    await page.evaluate((slug) => document.querySelector(`#${slug}-intake-form`)?.scrollIntoView({ block: 'start' }), vertical);
    await page.waitForTimeout(200);
    report.push({
      label: `${vertical[0].toUpperCase() + vertical.slice(1)} current grouped intake surface`,
      state: await page.evaluate(() => ({
        submit: document.querySelector('form button[type="submit"]')?.textContent.trim(),
        hasPerQuestionSkip: Boolean(document.querySelector('[data-baby-skip]')),
      })),
      screenshot: await viewportShot(page, `${vertical}-grouped-intake-readable`),
    });
  }

  await browser.close();

  const cards = report.map((item) => `
    <section class="card">
      <h2>${item.label}</h2>
      <pre>${JSON.stringify(item.state, null, 2)}</pre>
      <img src="${path.basename(item.screenshot)}" alt="${item.label}">
    </section>`).join('\n');
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Readable Intake Review</title><style>
    body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:24px;background:#f7f4ee;color:#172033;}
    h1{margin:0 0 8px;font-size:28px}.note{max-width:880px;line-height:1.45;margin:0 0 20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:24px}.card{background:white;border:1px solid #ddd4c8;border-radius:18px;padding:16px;box-shadow:0 10px 30px rgba(0,0,0,.06)}h2{font-size:18px;margin:0 0 10px}pre{white-space:pre-wrap;background:#f3f0ea;padding:10px;border-radius:10px;font-size:12px}img{display:block;width:390px;max-width:100%;height:auto;border-radius:12px;border:1px solid #e4ddd3;background:white;margin:auto;}
  </style></head><body><h1>Readable intake review: Skip → Next</h1><p class="note">Readable viewport/cropped review only — no full-page mobile skyscraper screenshots. Baby guided text field shows Skip while empty, Next after text. Pet/Business shown only as current grouped intake surfaces.</p><div class="grid">${cards}</div></body></html>`;
  fs.writeFileSync(path.join(OUT, 'review.html'), html);
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ reviewHtml: path.join(OUT, 'review.html'), screenshots: report.map(r => r.screenshot) }, null, 2));
})();
