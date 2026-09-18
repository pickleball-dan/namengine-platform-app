# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: baby.spec.js >> Baby — Card sizing (the standard) >> Question card fills mobile viewport — no artificial constraint
- Location: tests\e2e\baby.spec.js:62:3

# Error details

```
Error: Baby card width at mobile is 326px — expected >= 350px

expect(received).toBeGreaterThanOrEqual(expected)

Expected: >= 350
Received:    326
```

# Page snapshot

```yaml
- generic [ref=e1]:
  - banner [ref=e2]:
    - generic [ref=e3]:
      - link "Home" [ref=e4] [cursor=pointer]:
        - /url: /
      - navigation "Primary navigation" [ref=e6]:
        - button "What are you naming?" [ref=e8] [cursor=pointer]
  - main [ref=e12]:
    - generic [ref=e14]:
      - navigation "Baby name discovery navigation" [ref=e16]
      - generic [ref=e17]:
        - generic [ref=e18]:
          - paragraph [ref=e19]: About your baby
          - generic [ref=e21]:
            - heading "Any gender direction?" [level=2] [ref=e22]
            - generic [ref=e23]: Required
          - paragraph [ref=e24]: This helps us find names that feel just right.
          - generic [ref=e25]:
            - strong [ref=e26]: Let’s get to know your family.
            - progressbar "Interview progress" [ref=e27]
            - generic [ref=e29]: Question 1 of 13
          - radiogroup "Any gender direction?" [ref=e30]:
            - radio "Girl We’re expecting a baby girl." [active] [ref=e31] [cursor=pointer]:
              - generic [ref=e33]:
                - strong [ref=e34]: Girl
                - generic [ref=e35]: We’re expecting a baby girl.
              - generic [ref=e36]: ›
              - generic [ref=e37]: ✓
            - radio "Boy We’re expecting a baby boy." [ref=e38] [cursor=pointer]:
              - generic [ref=e40]:
                - strong [ref=e41]: Boy
                - generic [ref=e42]: We’re expecting a baby boy.
              - generic [ref=e43]: ›
              - generic [ref=e44]: ✓
            - radio "Gender-neutral We love names that work for any baby." [ref=e45] [cursor=pointer]:
              - generic [ref=e47]:
                - strong [ref=e48]: Gender-neutral
                - generic [ref=e49]: We love names that work for any baby.
              - generic [ref=e50]: ›
              - generic [ref=e51]: ✓
            - radio "Open to any Show us names for any gender." [ref=e52] [cursor=pointer]:
              - generic [ref=e54]:
                - strong [ref=e55]: Open to any
                - generic [ref=e56]: Show us names for any gender.
              - generic [ref=e57]: ›
              - generic [ref=e58]: ✓
          - combobox [ref=e59]
        - text: • • • • • •
      - navigation "Baby intake stages" [ref=e60]:
        - list [ref=e61]:
          - listitem [ref=e62]:
            - generic [ref=e63]: "1"
            - strong [ref=e64]: About your baby
          - listitem [ref=e65]:
            - generic [ref=e66]: "2"
            - strong [ref=e67]: Name style
          - listitem [ref=e68]:
            - generic [ref=e69]: "3"
            - strong [ref=e70]: Fit and feeling
        - paragraph [ref=e71]: ♡ Tell us what matters to your family. ♡
      - status [ref=e72]
      - button "Continue" [ref=e73] [cursor=pointer]
```

# Test source

```ts
  1   | 'use strict';
  2   | const { test, expect } = require('@playwright/test');
  3   | const { V, startInterview, visibleQuestion, answerAndAdvance, completeInterview, getCardSizing } = require('./helpers');
  4   | 
  5   | // ─── Standing rule: "Skip" must NEVER appear anywhere in Baby's interview ───
  6   | // The [data-baby-skip] button must always say "Next", never "Skip".
  7   | // This test will FAIL on production until the fix ships — that is intentional.
  8   | 
  9   | test.describe('Baby — Skip must never appear', () => {
  10  |   test('No visible "Skip" text at any point during the interview', async ({ page }) => {
  11  |     await startInterview(page, 'baby');
  12  | 
  13  |     for (let step = 0; step < 15; step++) {
  14  |       // Check the data-baby-skip button specifically
  15  |       const skipBtn = page.locator(`${V.baby.q}:not([hidden]) ${V.baby.skipNext}`);
  16  |       if (await skipBtn.count() > 0) {
  17  |         const label = (await skipBtn.textContent())?.trim();
  18  |         expect(
  19  |           label,
  20  |           `Step ${step + 1}: [data-baby-skip] reads "${label}" — must never say "Skip"`
  21  |         ).not.toBe('Skip');
  22  |       }
  23  | 
  24  |       // Check no visible element anywhere on the page says exactly "Skip"
  25  |       await expect(
  26  |         page.getByText('Skip', { exact: true }),
  27  |         `Step ${step + 1}: found a visible element with text "Skip"`
  28  |       ).toBeHidden();
  29  | 
  30  |       if (await page.locator(V.baby.complete).isVisible()) break;
  31  |       if (await page.locator(`${V.baby.q}:not([hidden])`).count() === 0) break;
  32  |       await answerAndAdvance(page, 'baby');
  33  |     }
  34  |   });
  35  | });
  36  | 
  37  | // ─── Baby — Card sizing (Baby IS the standard) ──────────────────────────────
  38  | // Desktop: max-width 760px, centered (margin auto).
  39  | // Mobile:  card fills viewport — width >= 350px.
  40  | // These values are the reference. Pet and Business must match.
  41  | 
  42  | // Baby IS the sizing standard — we verify it renders at a sane desktop width
  43  | // (>= 600px, <= viewport) and does not overflow at mobile.
  44  | // Pet and Business read Baby's computed width dynamically and must match it.
  45  | test.describe('Baby — Card sizing (the standard)', () => {
  46  |   test('Question card fills at least 65% of viewport — desktop', async ({ page }) => {
  47  |     const vp = page.viewportSize();
  48  |     if (vp.width < 1024) test.skip();
  49  | 
  50  |     await startInterview(page, 'baby');
  51  |     const sizing = await getCardSizing(page, V.baby.cardSel);
  52  |     expect(sizing, 'Could not read Baby question card sizing').not.toBeNull();
  53  | 
  54  |     // Standard: card must fill at least 65% of viewport. Baby defines this standard.
  55  |     // Pet and Business must meet the same threshold.
  56  |     expect(
  57  |       sizing.width,
  58  |       `Baby card width is ${sizing.width}px — must be >= 65% of ${vp.width}px viewport (${Math.round(vp.width * 0.65)}px)`
  59  |     ).toBeGreaterThanOrEqual(vp.width * 0.65);
  60  |   });
  61  | 
  62  |   test('Question card fills mobile viewport — no artificial constraint', async ({ page }) => {
  63  |     const vp = page.viewportSize();
  64  |     if (vp.width >= 1024) test.skip();
  65  | 
  66  |     await startInterview(page, 'baby');
  67  |     const sizing = await getCardSizing(page, V.baby.cardSel);
  68  |     expect(sizing, 'Could not read Baby question card sizing').not.toBeNull();
  69  | 
  70  |     expect(
  71  |       sizing.width,
  72  |       `Baby card width at mobile is ${sizing.width}px — expected >= 350px`
> 73  |     ).toBeGreaterThanOrEqual(350);
      |       ^ Error: Baby card width at mobile is 326px — expected >= 350px
  74  |   });
  75  | });
  76  | 
  77  | // ─── Baby interview flow ─────────────────────────────────────────────────────
  78  | 
  79  | test.describe('Baby — Interview flow', () => {
  80  |   test.beforeEach(async ({ page }) => {
  81  |     await startInterview(page, 'baby');
  82  |   });
  83  | 
  84  |   test('Exactly one question is visible at a time after Begin', async ({ page }) => {
  85  |     await expect(page.locator(`${V.baby.q}:not([hidden])`)).toHaveCount(1);
  86  |   });
  87  | 
  88  |   test('Back returns to the previous question', async ({ page }) => {
  89  |     const q1Id = await visibleQuestion(page, 'baby').getAttribute('data-question-id');
  90  | 
  91  |     await answerAndAdvance(page, 'baby');
  92  | 
  93  |     const q2Id = await visibleQuestion(page, 'baby').getAttribute('data-question-id');
  94  |     expect(q2Id).not.toBe(q1Id);
  95  | 
  96  |     await page.locator(V.baby.back).click();
  97  |     await page.waitForTimeout(300);
  98  | 
  99  |     expect(
  100 |       await visibleQuestion(page, 'baby').getAttribute('data-question-id')
  101 |     ).toBe(q1Id);
  102 |   });
  103 | 
  104 |   test('Interview shows direction review then completion screen', async ({ page }) => {
  105 |     // Baby now has direction review before completion.
  106 |     // Walk to direction review, click Find our name, completion panel appears briefly.
  107 |     const result = await completeInterview(page, 'baby');
  108 |     // Baby goes to direction review (no hasReview flag — check manually)
  109 |     const review = page.locator('[data-baby-direction-review]:not([hidden])');
  110 |     if (await review.count() > 0) {
  111 |       await page.locator('[data-baby-direction-find]').click();
  112 |       await page.waitForTimeout(800);
  113 |     }
  114 |     await expect(page.locator(V.baby.complete)).toBeVisible({ timeout: 5000 });
  115 |   });
  116 | });
  117 | 
  118 | 
  119 | 
```