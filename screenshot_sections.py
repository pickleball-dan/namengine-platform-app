import asyncio
from playwright.async_api import async_playwright

async def go():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        await page.goto('http://127.0.0.1:5000', wait_until='networkidle')
        await page.wait_for_timeout(800)
        scrolls = [900, 1800, 2700, 3600]
        for i, scroll in enumerate(scrolls):
            await page.evaluate(f'window.scrollTo(0, {scroll})')
            await page.wait_for_timeout(400)
            clip = {'x': 0, 'y': 0, 'width': 390, 'height': 844}
            await page.screenshot(path=f'static/images/page-section-{i+1}.png', clip=clip)
        await browser.close()
        print('done')

asyncio.run(go())
