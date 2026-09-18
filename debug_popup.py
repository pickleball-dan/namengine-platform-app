import asyncio
from playwright.async_api import async_playwright

async def go():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)

        errors = []
        page.on('console', lambda msg: print(f'CONSOLE [{msg.type}]: {msg.text}'))
        page.on('pageerror', lambda err: errors.append(str(err)))

        await page.goto('http://127.0.0.1:5000', wait_until='networkidle')
        await page.wait_for_timeout(1000)

        # Check JS loaded
        js_loaded = await page.evaluate("""() =>
            [...document.querySelectorAll('script[src]')].map(s => s.src)
        """)
        print('Scripts loaded:')
        for s in js_loaded: print(' ', s)

        # Check popup exists in DOM
        popup_exists = await page.evaluate("() => !!document.getElementById('landing-popup')")
        print('Popup in DOM:', popup_exists)

        # Check pills exist
        pills = await page.evaluate("() => document.querySelectorAll('.landing-pill').length")
        print('Pills found:', pills)

        # Try clicking Baby pill
        pill = page.locator('.landing-pill-baby')
        if await pill.count() > 0:
            await pill.click()
            await page.wait_for_timeout(500)
            popup_active = await page.evaluate("() => document.getElementById('landing-popup')?.classList.contains('active')")
            print('Popup active after pill click:', popup_active)
            await page.screenshot(path='static/images/debug-popup-click.png', clip={'x':0,'y':0,'width':390,'height':844})
        else:
            print('Baby pill NOT FOUND')

        if errors:
            print('JS ERRORS:', errors)

        await browser.close()

asyncio.run(go())
