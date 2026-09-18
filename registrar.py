import os
import asyncio
from playwright.async_api import async_playwright

URL = "https://in.mpms.mufg.com/Initial_Offer/public-issues.html"

async def check_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        await page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        text = await page.locator("body").inner_text()

        print("PAGE CONTENT:")
        print(text[:5000])

        if "manika" in text.lower():
            print("MANIKA FOUND IN RENDERED PAGE")
        else:
            print("MANIKA NOT FOUND")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_page())
