import asyncio
from playwright.async_api import async_playwright

async def diagnose():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 390, 'height': 844})
        await page.goto('http://127.0.0.1:5000', wait_until='networkidle')

        # Check CSS files loading
        css = await page.evaluate("""() =>
            [...document.querySelectorAll("link[rel='stylesheet']")].map(l => l.href)
        """)
        print("CSS loaded:")
        for c in css: print(" ", c)

        # Body class
        body_class = await page.evaluate("() => document.body.className")
        print("Body class:", repr(body_class))

        # hero display
        hero_display = await page.evaluate("""() => {
            const h = document.querySelector('.landing-hero');
            if (!h) return 'NOT FOUND';
            return window.getComputedStyle(h).display;
        }""")
        print("Hero display:", hero_display)

        # main width
        main_w = await page.evaluate("""() => {
            const m = document.querySelector('main');
            if (!m) return 'NOT FOUND';
            return m.getBoundingClientRect().width;
        }""")
        print("Main width:", main_w)

        # Find overflowing elements
        overflow = await page.evaluate("""() => {
            const results = [];
            const vw = document.documentElement.clientWidth;
            document.querySelectorAll('*').forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.right > vw + 2 || r.left < -2) {
                    results.push({
                        tag: el.tagName,
                        cls: (el.className || '').toString().slice(0, 80),
                        w: Math.round(r.width),
                        left: Math.round(r.left),
                        right: Math.round(r.right),
                        vw: vw
                    });
                }
            });
            return results.slice(0, 15);
        }""")
        print(f"\nOverflowing elements (vw=390):")
        for el in overflow:
            print(f"  {el['tag']} | .{el['cls']}")
            print(f"    w={el['w']} left={el['left']} right={el['right']}")

        await browser.close()

asyncio.run(diagnose())
