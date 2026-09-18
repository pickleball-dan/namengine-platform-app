const { chromium } = require('playwright');
const http = require('http');

const BASE = 'http://127.0.0.1:5001';

async function getSessionId() {
  return new Promise((resolve, reject) => {
    const url = `${BASE}/baby/results?gender=Girl&style=Classic&sound=Soft`;
    http.get(url, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        const m = data.match(/data-session-id="(baby-[a-f0-9]+)"/);
        resolve(m ? m[1] : null);
      });
    }).on('error', reject);
  });
}

(async () => {
  const browser = await chromium.launch();
  const sessionId = await getSessionId();
  if (!sessionId) { console.error('Could not get session id'); await browser.close(); process.exit(1); }
  console.log('Session:', sessionId);

  // --- LOCKED view (no cookie) ---
  const lockedCtx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const lockedPage = await lockedCtx.newPage();
  await lockedPage.goto(`${BASE}/share/${sessionId}`, { waitUntil: 'domcontentloaded' });
  await lockedPage.screenshot({ path: 'tmp_share_locked_mobile.png', fullPage: true });
  console.log('Locked screenshot: tmp_share_locked_mobile.png');

  // Desktop locked
  const lockedDeskCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const lockedDeskPage = await lockedDeskCtx.newPage();
  await lockedDeskPage.goto(`${BASE}/share/${sessionId}`, { waitUntil: 'domcontentloaded' });
  await lockedDeskPage.screenshot({ path: 'tmp_share_locked_desktop.png', fullPage: true });
  console.log('Locked desktop screenshot: tmp_share_locked_desktop.png');

  // --- click a premium action to trigger the popup ---
  await lockedPage.locator('[data-premium-action]').first().click();
  await lockedPage.waitForTimeout(400);
  await lockedPage.screenshot({ path: 'tmp_share_popup_mobile.png' });
  console.log('Popup screenshot: tmp_share_popup_mobile.png');

  await browser.close();
  console.log('Done.');
})();
