import asyncio
from playwright.async_api import async_playwright

URL = "https://in.mpms.mufg.com/Initial_Offer/public-issues.html"


async def inspect_company():
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

        print("\n--- PAGE LOADED ---")

        selects = page.locator("select")

        print("Select count:", await selects.count())

        for i in range(await selects.count()):

            select = selects.nth(i)

            print("\nSelect:", i)
            print("ID:", await select.get_attribute("id"))
            print("Name:", await select.get_attribute("name"))

        print("\n--- SELECT MANIKA PLASTECH ---")

        manika = page.locator(
            'option[value="11937"]'
        )

        print("Manika option count:", await manika.count())

        if await manika.count() == 0:

            print("Manika option not found.")

        else:

            parent_select = manika.locator("xpath=..")

            await parent_select.select_option("11937")

            print("Manika selected successfully.")

            await page.wait_for_timeout(5000)

        print("\n--- PAGE CONTENT AFTER SELECTION ---")

        text = await page.locator("body").inner_text()

        print(text[:10000])

        print("\n--- ALL INPUT FIELDS ---")

        inputs = page.locator("input")

        for i in range(await inputs.count()):

            field = inputs.nth(i)

            print(
                "Input",
                i,
                "| type:",
                await field.get_attribute("type"),
                "| name:",
                await field.get_attribute("name"),
                "| id:",
                await field.get_attribute("id"),
                "| placeholder:",
                await field.get_attribute("placeholder")
            )

        await browser.close()


if __name__ == "__main__":

    asyncio.run(inspect_company())
