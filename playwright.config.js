'use strict';
const { defineConfig } = require('@playwright/test');

// Default: production. Override with BASE_URL env var for local testing.
// Usage:
//   npx playwright test                          → runs against https://nam-engine.com
//   BASE_URL=http://localhost:5000 npx playwright test  → runs locally

module.exports = defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  retries: 0,
  reporter: 'list',
  timeout: 60000,

  use: {
    baseURL: process.env.BASE_URL || 'https://nam-engine.com',
    headless: true,
    screenshot: 'only-on-failure',
    contextOptions: {
      // Always run as unauthenticated visitor — no cookies, no session state
      storageState: undefined,
    },
  },

  projects: [
    {
      name: 'desktop',
      use: { viewport: { width: 1280, height: 800 } },
    },
    {
      name: 'mobile',
      use: { viewport: { width: 390, height: 844 } },
    },
  ],
});
