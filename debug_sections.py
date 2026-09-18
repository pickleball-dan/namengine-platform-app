import asyncio
from playwright.async_api import async_playwright

async def go():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        await page.goto('http://127.0.0.1:5000', wait_until='networkidle')
        await page.wait_for_timeout(800)

        # Check all major sections
        sections = await page.evaluate("""() => {
            const sels = [
                '.landing-hero',
                '.landing-trust-strip',
                '#naming-experiences',
                '#pricing',
                '#how-it-works',
                '#why-different',
                '.landing-matters',
                '.landing-final',
                'footer'
            ];
            return sels.map(s => {
                const el = document.querySelector(s);
                if (!el) return {sel: s, found: false};
                const r = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return {
                    sel: s,
                    found: true,
                    display: style.display,
                    visibility: style.visibility,
                    height: Math.round(r.height),
                    top: Math.round(r.top + window.scrollY)
                };
            });
        }""")
        for s in sections:
            if s['found']:
                print(f"{s['sel']}: display={s['display']} h={s['height']}px top={s['top']}px")
            else:
                print(f"{s['sel']}: NOT FOUND")

        total_h = await page.evaluate('() => document.body.scrollHeight')
        print(f"\nTotal scroll height: {total_h}px")

        await browser.close()

asyncio.run(go())
