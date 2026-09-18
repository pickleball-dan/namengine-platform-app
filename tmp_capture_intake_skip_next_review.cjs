const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:5000';
const OUT = path.join('qa-artifacts', 'intake-text-skip-next-review-20260819-1021');
fs.mkdirSync(OUT, { recursive: true });

async function snapshot(page, name) {
  const shot = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: shot, fullPage: true });
  return shot;
}

async function forceStartInterview(page) {
  await page.evaluate(() => {
    document.body.classList.add('baby-interview-started');
    const first = document.querySelector('[data-baby-question]');
    document.querySelectorAll('[data-baby-question]').forEach((q) => {
      const active = q === first;
      q.hidden = !active;
      q.classList.toggle('is-active', active);
    });
    document.querySelector('[data-baby-question-stage]')?.removeAttribute('hidden');
  });
}

async function buttonState(page) {
  return await page.evaluate(() => {
    const q = document.querySelector('[data-baby-question]:not([hidden])');
    const input = q && q.querySelector('textarea, input:not([type="hidden"]):not([data-other-input])');
    const skip = q && q.querySelector('[data-baby-skip]');
    const cont = q && q.querySelector('[data-baby-continue]');
    return {
      questionId: q && q.dataset.questionId,
      questionKind: q && q.dataset.questionKind,
      value: input && input.value,
      skipText: skip && skip.textContent.trim(),
      skipActionState: skip && skip.dataset.actionState,
      skipAriaLabel: skip && skip.getAttribute('aria-label'),
      continueText: cont && cont.textContent.trim(),
    };
  });
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
    const q = document.querySelector(`[data-question-id="${questionId}"]`);
    q?.querySelector('textarea, input:not([type="hidden"]):not([data-other-input])')?.focus({ preventScroll: true });
  }, id);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });
  const report = [];

  await page.goto(`${BASE}/baby`, { waitUntil: 'networkidle' });
  await forceStartInterview(page);
  await showQuestion(page, 'family_context');
  await page.waitForSelector('[data-question-id="family_context"]:not([hidden])');
  report.push({ vertical: 'baby', state: 'empty_optional_text', data: await buttonState(page), screenshot: await snapshot(page, 'baby-family-context-empty-skip') });

  await page.locator('[data-question-id="family_context"] textarea, [data-question-id="family_context"] input:not([type="hidden"])').fill('Last name Parker; we like soft classic names.');
  await page.waitForTimeout(100);
  report.push({ vertical: 'baby', state: 'typed_optional_text', data: await buttonState(page), screenshot: await snapshot(page, 'baby-family-context-typed-next') });

  await page.keyboard.press('Enter');
  await page.waitForTimeout(350);
  report.push({ vertical: 'baby', state: 'after_enter', data: await buttonState(page), screenshot: await snapshot(page, 'baby-after-enter-next-question') });

  for (const vertical of ['pet', 'business']) {
    await page.goto(`${BASE}/${vertical}`, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.querySelector('#pet-intake-form, #business-intake-form')?.scrollIntoView());
    report.push({
      vertical,
      state: 'current_intake_surface_no_per_question_skip',
      data: await page.evaluate(() => ({
        hasGuidedQuestions: Boolean(document.querySelector('[data-baby-question]')),
        visibleSkipButtons: Array.from(document.querySelectorAll('[data-baby-skip]')).filter((el) => !el.closest('[hidden]')).map((el) => el.textContent.trim()),
        submitText: document.querySelector('form button[type="submit"]')?.textContent.trim(),
        textInputs: Array.from(document.querySelectorAll('textarea, input:not([type="hidden"]):not([data-other-input])')).slice(0, 6).map((el) => ({ id: el.id, placeholder: el.getAttribute('placeholder'), value: el.value }))
      })),
      screenshot: await snapshot(page, `${vertical}-current-intake-surface`)
    });
  }

  await browser.close();

  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Intake Skip to Next Review</title><style>body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:32px;background:#f7f4ee;color:#172033}h1{margin-bottom:0}.note{max-width:820px;line-height:1.45}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin-top:24px}.card{background:white;border:1px solid #ddd4c8;border-radius:18px;padding:16px;box-shadow:0 10px 30px rgba(0,0,0,.06)}img{width:100%;border-radius:12px;border:1px solid #e4ddd3}pre{white-space:pre-wrap;background:#f3f0ea;padding:12px;border-radius:10px;font-size:12px}</style></head><body><h1>Intake text action review: Skip → Next</h1><p class="note">Local-only review artifact. Baby guided optional text questions now show <strong>Skip</strong> while empty and <strong>Next</strong> after non-whitespace text is entered. Pressing Enter still saves and advances. Pet and Business screenshots are included to show their current intake surfaces; they currently use a grouped form submit button, not the same per-question Skip control.</p><div class="grid">${report.map((item) => `<section class="card"><h2>${item.vertical}: ${item.state}</h2><pre>${JSON.stringify(item.data, null, 2)}</pre><img src="${path.basename(item.screenshot)}" alt="${item.vertical} ${item.state}"></section>`).join('')}</div></body></html>`;
  fs.writeFileSync(path.join(OUT, 'review.html'), html);
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ out: OUT, reviewHtml: path.join(OUT, 'review.html'), report }, null, 2));
})();
