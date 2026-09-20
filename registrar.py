import asyncio
from playwright.async_api import async_playwright

URL = "https://in.mpms.mufg.com/Initial_Offer/public-issues.html"


async def inspect_logic():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        print("\n--- BASIS OF ALLOTMENT LINKS ---")

        links = page.locator("a")

        for i in range(await links.count()):

            link = links.nth(i)

            text = (await link.inner_text()).strip()

            href = await link.get_attribute("href")

            if "allot" in text.lower() or "allot" in str(href).lower():

                print(f"Text: {text}")
                print(f"Href: {href}")
                print()

        print("\n--- SEARCH FUNCTION ---")

        function_info = await page.evaluate("""
        () => {
            if (typeof CALLPANSERCH === 'function') {
                return CALLPANSERCH.toString();
            }
            return 'CALLPANSERCH not found';
        }
        """)

        print(function_info)

        print("\n--- PAGE SCRIPTS ---")

        scripts = await page.locator("script").all()

        for i, script in enumerate(scripts):

            src = await script.get_attribute("src")

            if src:
                print(f"Script {i}: {src}")

        await browser.close()


if __name__ == "__main__":

    asyncio.run(inspect_logic())
