import asyncio
from playwright.async_api import async_playwright

URL = "https://ipostatus1.cameoindia.com/"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Opening Cameo IPO status portal...")
        await page.goto(URL, wait_until="networkidle")

        options = await page.locator("#drpCompany option").all()
        print(f"Company options: {len(options)}")

        print("\nChecking all companies...\n")

        for option in options:
            value = await option.get_attribute("value")
            text = (await option.inner_text()).strip()

            if not value or value == "0":
                continue

            await page.select_option("#drpCompany", value=value)
            await page.evaluate("GetMaster1Details()")

            button = page.locator("#view_button")

            display = await button.evaluate(
                "(el) => getComputedStyle(el).display"
            )
            href = await button.get_attribute("href")

            print(f"{value:5} | {text}")

            if display != "none" or href:
                print(f"      >>> BASIS AVAILABLE")
                print(f"      >>> href: {href}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
