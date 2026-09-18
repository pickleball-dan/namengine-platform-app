const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const page = await b.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://localhost:5000/business', { waitUntil: 'networkidle' });

  // Get the logo bounding box and screenshot just that area
  const box = await page.locator('.vertical-page-logo').first().boundingBox();
  console.log('Logo box:', box);

  if (box) {
    // Expand the clip to include some dark background context
    await page.screenshot({
      path: 'tmp_logo_closeup.png',
      clip: {
        x: Math.max(0, box.x - 10),
        y: Math.max(0, box.y - 20),
        width: Math.min(400, box.width + 20),
        height: box.height + 40,
      }
    });
  }

  await b.close();
  console.log('done');
})();
