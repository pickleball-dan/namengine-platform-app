const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();

  // 1. Business access/unlock page
  await page.goto('http://127.0.0.1:5001/business/access', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'tmp_ss_business_access.png', fullPage: true });
  console.log('1. Access page done');

  // 2. Business intake welcome
  await page.goto('http://127.0.0.1:5001/business/intake', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'tmp_ss_business_intake.png', fullPage: false });
  console.log('2. Intake welcome done');

  // 3. Click begin (anchor scroll) then screenshot the form area
  await page.locator('.baby-begin-button').first().click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'tmp_ss_business_intake_form.png', fullPage: false });
  console.log('3. Intake form area done');

  await browser.close();
})();
