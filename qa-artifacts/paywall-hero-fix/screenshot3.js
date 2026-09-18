const { chromium } = require('playwright');

(async () => {
  const br = await chromium.launch();
  const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } });

  const sessions = [
    { label: '04-baby-results', url: 'http://127.0.0.1:5000/results/session/baby-7aaca470e7fa' },
    { label: '05-pet-results',  url: 'http://127.0.0.1:5000/results/session/pet-ff8289c94bdc'  },
  ];

  for (const s of sessions) {
    const pg = await ctx.newPage();
    await pg.goto(s.url, { waitUntil: 'domcontentloaded', timeout: 10000 });
    await pg.waitForTimeout(700);
    await pg.screenshot({ path: `qa-artifacts/paywall-hero-fix/${s.label}.png`, fullPage: false });
    console.log(s.label, 'done, url:', pg.url());
    await pg.close();
  }

  await br.close();
})();
