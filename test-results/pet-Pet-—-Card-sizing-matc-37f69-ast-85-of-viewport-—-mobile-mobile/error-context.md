# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: pet.spec.js >> Pet — Card sizing matches Baby standard >> Question card fills at least 85% of viewport — mobile
- Location: tests\e2e\pet.spec.js:49:3

# Error details

```
Error: Pet card width (300px) must be >= 85% of 390px mobile viewport (332px)

expect(received).toBeGreaterThanOrEqual(expected)

Expected: >= 331.5
Received:    300
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
      - generic [ref=e15]:
        - navigation "Pet name discovery navigation"
      - generic [ref=e16]:
        - text: 🐾
        - generic [ref=e17]:
          - text: 🐾
          - paragraph [ref=e18]: 🐾 About your pet
          - generic [ref=e19]:
            - heading "Who's joining the family?" [level=2] [ref=e20]
            - generic [ref=e21]: Required
          - radiogroup "Who's joining the family?" [ref=e22]:
            - radio "Dog Loyal, playful, full of personality" [active] [ref=e23] [cursor=pointer]:
              - generic [ref=e24]: 🐕
              - generic [ref=e25]:
                - strong [ref=e26]: Dog
                - generic [ref=e27]: Loyal, playful, full of personality
              - generic [ref=e28]: ✓
            - radio "Cat Independent, curious, a little mysterious" [ref=e29] [cursor=pointer]:
              - generic [ref=e30]: 🐈
              - generic [ref=e31]:
                - strong [ref=e32]: Cat
                - generic [ref=e33]: Independent, curious, a little mysterious
              - generic [ref=e34]: ✓
            - radio "Horse Majestic, powerful, deeply bonded" [ref=e35] [cursor=pointer]:
              - generic [ref=e36]: 🐴
              - generic [ref=e37]:
                - strong [ref=e38]: Horse
                - generic [ref=e39]: Majestic, powerful, deeply bonded
              - generic [ref=e40]: ✓
            - radio "Bird Feathered, expressive, vocal" [ref=e41] [cursor=pointer]:
              - generic [ref=e42]: 🦜
              - generic [ref=e43]:
                - strong [ref=e44]: Bird
                - generic [ref=e45]: Feathered, expressive, vocal
              - generic [ref=e46]: ✓
            - radio "Rabbit Soft, curious, unexpectedly funny" [ref=e47] [cursor=pointer]:
              - generic [ref=e48]: 🐰
              - generic [ref=e49]:
                - strong [ref=e50]: Rabbit
                - generic [ref=e51]: Soft, curious, unexpectedly funny
              - generic [ref=e52]: ✓
            - radio "Reptile Cool, calm, their own kind of personality" [ref=e53] [cursor=pointer]:
              - generic [ref=e54]: 🦎
              - generic [ref=e55]:
                - strong [ref=e56]: Reptile
                - generic [ref=e57]: Cool, calm, their own kind of personality
              - generic [ref=e58]: ✓
            - radio "Other Every companion deserves a great name" [ref=e59] [cursor=pointer]:
              - generic [ref=e60]: 🐾
              - generic [ref=e61]:
                - strong [ref=e62]: Other
                - generic [ref=e63]: Every companion deserves a great name
              - generic [ref=e64]: ✓
          - textbox [ref=e65]
          - textbox "Enter your own" [disabled] [ref=e66]
          - generic [ref=e67]:
            - button "Back" [ref=e68] [cursor=pointer]
            - button "Next" [ref=e69] [cursor=pointer]
        - text: 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾 🐾
      - generic [ref=e70]:
        - progressbar "Interview progress" [ref=e71]
        - text: Question 1 of 12
      - status [ref=e73]
      - button "Find names"
```

# Test source

```ts
  1   | 'use strict';
  2   | const { test, expect } = require('@playwright/test');
  3   | const { V, startInterview, visibleQuestion, answerAndAdvance, completeInterview, getCardSizing } = require('./helpers');
  4   | 
  5   | // ─── Standing rule: "Skip" must NEVER appear anywhere in Pet's interview ─────
  6   | 
  7   | test.describe('Pet — Skip must never appear', () => {
  8   |   test('No visible "Skip" text at any point during the interview', async ({ page }) => {
  9   |     await startInterview(page, 'pet');
  10  | 
  11  |     for (let step = 0; step < 20; step++) {
  12  |       await expect(
  13  |         page.getByText('Skip', { exact: true }),
  14  |         `Step ${step + 1}: found a visible element with text "Skip" in Pet interview`
  15  |       ).toBeHidden();
  16  | 
  17  |       if (await page.locator(V.pet.review).isVisible()) break;
  18  |       if (await page.locator(`${V.pet.q}:not([hidden])`).count() === 0) break;
  19  |       await answerAndAdvance(page, 'pet');
  20  |     }
  21  |   });
  22  | });
  23  | 
  24  | // ─── Pet — Card sizing must match Baby standard ───────────────────────────────
  25  | // Baby is the declared standard. Pet must match at every viewport.
  26  | // Desktop: max-width 760px, centered. Mobile: width >= 350px.
  27  | // These tests WILL FAIL on production until the CSS fix ships — that is intentional.
  28  | 
  29  | // Pet card sizing is measured against Baby's live computed values.
  30  | // Baby is navigated first to get the reference width, then Pet is checked.
  31  | // Tolerance: 50px — accounts for minor padding differences between verticals.
  32  | // Standard: card must fill >= 65% of viewport at desktop, >= 85% at mobile.
  33  | // Baby meets this standard. Pet and Business must match it independently.
  34  | test.describe('Pet — Card sizing matches Baby standard', () => {
  35  |   test('Question card fills at least 65% of viewport — desktop', async ({ page }) => {
  36  |     const vp = page.viewportSize();
  37  |     if (vp.width < 1024) test.skip();
  38  | 
  39  |     await startInterview(page, 'pet');
  40  |     const sizing = await getCardSizing(page, V.pet.cardSel);
  41  |     expect(sizing, 'Could not read Pet card sizing').not.toBeNull();
  42  | 
  43  |     expect(
  44  |       sizing.width,
  45  |       `Pet card width (${sizing.width}px) must be >= 65% of ${vp.width}px viewport (${Math.round(vp.width * 0.65)}px)`
  46  |     ).toBeGreaterThanOrEqual(vp.width * 0.65);
  47  |   });
  48  | 
  49  |   test('Question card fills at least 85% of viewport — mobile', async ({ page }) => {
  50  |     const vp = page.viewportSize();
  51  |     if (vp.width >= 1024) test.skip();
  52  | 
  53  |     await startInterview(page, 'pet');
  54  |     const sizing = await getCardSizing(page, V.pet.cardSel);
  55  |     expect(sizing, 'Could not read Pet card sizing').not.toBeNull();
  56  | 
  57  |     expect(
  58  |       sizing.width,
  59  |       `Pet card width (${sizing.width}px) must be >= 85% of ${vp.width}px mobile viewport (${Math.round(vp.width * 0.85)}px)`
> 60  |     ).toBeGreaterThanOrEqual(vp.width * 0.85);
      |       ^ Error: Pet card width (300px) must be >= 85% of 390px mobile viewport (332px)
  61  |   });
  62  | });
  63  | 
  64  | // ─── Pet interview flow ──────────────────────────────────────────────────────
  65  | 
  66  | test.describe('Pet — Interview flow', () => {
  67  |   test.beforeEach(async ({ page }) => {
  68  |     await startInterview(page, 'pet');
  69  |   });
  70  | 
  71  |   test('Exactly one question is visible at a time after Begin', async ({ page }) => {
  72  |     await expect(page.locator(`${V.pet.q}:not([hidden])`)).toHaveCount(1);
  73  |   });
  74  | 
  75  |   test('Next on an empty optional text question advances without blocking', async ({ page }) => {
  76  |     let tested = false;
  77  | 
  78  |     for (let i = 0; i < 15; i++) {
  79  |       if (await page.locator(V.pet.review).isVisible()) break;
  80  | 
  81  |       const q = visibleQuestion(page, 'pet');
  82  |       await q.waitFor({ state: 'visible' });
  83  |       const kind = await q.getAttribute('data-question-kind');
  84  |       const required = await q.getAttribute('data-required');
  85  | 
  86  |       if ((kind === 'text' || kind === 'textarea') && required === 'false') {
  87  |         const beforeId = await q.getAttribute('data-question-id');
  88  |         // Click Next without filling anything
  89  |         await q.locator(V.pet.next).click();
  90  |         await page.waitForTimeout(500);
  91  | 
  92  |         // Must advance — either to next question or direction review
  93  |         const reviewNow = await page.locator(V.pet.review).isVisible();
  94  |         if (!reviewNow) {
  95  |           const afterId = await visibleQuestion(page, 'pet').getAttribute('data-question-id');
  96  |           expect(afterId, 'Optional empty Next must advance to a different question').not.toBe(beforeId);
  97  |         }
  98  |         tested = true;
  99  |         break;
  100 |       }
  101 | 
  102 |       await answerAndAdvance(page, 'pet');
  103 |     }
  104 | 
  105 |     if (!tested) {
  106 |       console.log('NOTE: No optional text question encountered in first 15 steps — verify Pet question config');
  107 |     }
  108 |   });
  109 | 
  110 |   test('Back returns to the previous question', async ({ page }) => {
  111 |     const q1Id = await visibleQuestion(page, 'pet').getAttribute('data-question-id');
  112 | 
  113 |     await answerAndAdvance(page, 'pet');
  114 | 
  115 |     const q2Id = await visibleQuestion(page, 'pet').getAttribute('data-question-id');
  116 |     expect(q2Id).not.toBe(q1Id);
  117 | 
  118 |     await page.locator(V.pet.back).click();
  119 |     await page.waitForTimeout(300);
  120 | 
  121 |     expect(
  122 |       await visibleQuestion(page, 'pet').getAttribute('data-question-id')
  123 |     ).toBe(q1Id);
  124 |   });
  125 | 
  126 |   test('Direction review appears after all questions — not results', async ({ page }) => {
  127 |     const result = await completeInterview(page, 'pet');
  128 |     expect(result, 'Must reach direction review, not bypass to complete or max-reached').toBe('review');
  129 |     await expect(page.locator(V.pet.review)).toBeVisible();
  130 |   });
  131 | 
  132 |   test('Direction review has an Edit button for every question', async ({ page }) => {
  133 |     await completeInterview(page, 'pet');
  134 |     const allQuestions = await page.locator(V.pet.q).count();
  135 |     const editButtons = page.locator(`${V.pet.review} [data-edit-question]`);
  136 |     await expect(editButtons).toHaveCount(allQuestions);
  137 |   });
  138 | 
  139 |   test('Edit from direction review navigates to that specific question', async ({ page }) => {
  140 |     await completeInterview(page, 'pet');
  141 | 
  142 |     const firstEdit = page.locator(`${V.pet.review} [data-edit-question]`).first();
  143 |     const targetId = await firstEdit.getAttribute('data-edit-question');
  144 |     await firstEdit.click();
  145 |     await page.waitForTimeout(400);
  146 | 
  147 |     expect(
  148 |       await visibleQuestion(page, 'pet').getAttribute('data-question-id')
  149 |     ).toBe(targetId);
  150 |     await expect(page.locator(V.pet.review)).toBeHidden();
  151 |   });
  152 | 
  153 |   test('After editing a question, direction review reappears', async ({ page }) => {
  154 |     await completeInterview(page, 'pet');
  155 | 
  156 |     const firstEdit = page.locator(`${V.pet.review} [data-edit-question]`).first();
  157 |     await firstEdit.click();
  158 |     await page.waitForTimeout(400);
  159 | 
  160 |     // Review must be hidden while editing
```