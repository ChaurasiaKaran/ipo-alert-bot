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

        # Test only the first real company
        for option in options:
            value = await option.get_attribute("value")
            text = (await option.inner_text()).strip()

            if not value:
                continue

            print(f"\nTesting: {text}")
            print(f"Value: {value}")

            await page.select_option("#drpCompany", value=value)

            print("Selected dropdown.")

            # The site's onchange calls GetMaster1Details()
            await page.evaluate("GetMaster1Details()")

            print("Called GetMaster1Details().")

            button = page.locator("#view_button")

            print("Button count:", await button.count())
            print("Button display:",
                  await button.evaluate("(el) => el.style.display"))
            print("Button href:",
                  await button.get_attribute("href"))

            break

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
