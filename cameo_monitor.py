import asyncio
from playwright.async_api import async_playwright

CAMEO_URL = "https://ipostatus1.cameoindia.com/"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Opening Cameo IPO status portal...")
        await page.goto(CAMEO_URL, wait_until="networkidle")

        options = await page.locator("#drpCompany option").all()

        print(f"Company options: {len(options)}")
        print()

        for option in options:
            value = await option.get_attribute("value")
            text = (await option.inner_text()).strip()

            if not value:
                continue

            # Actually trigger the website's onchange handler
            await page.select_option("#drpCompany", value=value)
            await page.locator("#drpCompany").dispatch_event("change")

            await page.wait_for_timeout(300)

            button = page.locator("#view_button")

            display = await button.evaluate(
                "(el) => getComputedStyle(el).display"
            )
            href = await button.get_attribute("href")

            if display != "none" or href:
                print("FOUND BASIS LINK")
                print(f"Company: {text}")
                print(f"Value: {value}")
                print(f"Display: {display}")
                print(f"Href: {href}")
                print("-" * 60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
