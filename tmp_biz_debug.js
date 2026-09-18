const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const page = await b.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://localhost:5000/business', { waitUntil: 'networkidle' });

  // Find the logo and get computed styles
  const logoInfo = await page.evaluate(() => {
    const logo = document.querySelector('.vertical-page-logo');
    if (!logo) return { error: 'no logo found' };
    const cs = window.getComputedStyle(logo);
    return {
      src: logo.src,
      filter: cs.filter,
      opacity: cs.opacity,
      display: cs.display,
      visibility: cs.visibility,
      width: cs.width,
      parentClass: logo.parentElement?.className,
      grandparentClass: logo.parentElement?.parentElement?.className,
    };
  });

  console.log('Logo info:', JSON.stringify(logoInfo, null, 2));

  // Also check body data attributes
  const bodyAttrs = await page.evaluate(() => {
    const b = document.body;
    return {
      classes: b.className,
      pageData: b.getAttribute('data-page-dark'),
      hasDarkLogo: b.getAttribute('data-has-dark-logo'),
    };
  });
  console.log('Body:', JSON.stringify(bodyAttrs, null, 2));

  await b.close();
})();
