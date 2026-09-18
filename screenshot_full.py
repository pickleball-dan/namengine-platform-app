import asyncio
from playwright.async_api import async_playwright

async def go():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        await page.goto('http://127.0.0.1:5000', wait_until='networkidle')
        await page.wait_for_timeout(1000)

        # Get full page height
        height = await page.evaluate('() => document.body.scrollHeight')
        print(f'Full page height: {height}px')

        # Take overlapping screenshots every 700px
        step = 700
        i = 0
        pos = 0
        while pos < height:
            await page.evaluate(f'window.scrollTo(0, {pos})')
            await page.wait_for_timeout(300)
            clip = {'x': 0, 'y': 0, 'width': 390, 'height': 844}
            await page.screenshot(path=f'static/images/full-page-{i:02d}.png', clip=clip)
            print(f'  Screenshot {i}: scroll={pos}')
            pos += step
            i += 1

        await browser.close()
        print('done')

asyncio.run(go())
