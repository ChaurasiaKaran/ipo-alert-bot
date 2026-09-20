import asyncio

from playwright.async_api import async_playwright


CAMEO_URL = "https://ipostatus1.cameoindia.com/"


async def check_cameo():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print("Opening Cameo IPO status portal...")

        await page.goto(
            CAMEO_URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        print("Page title:", await page.title())

        # Select elements
        selects = page.locator("select")

        print(
            "\nSelect elements:",
            await selects.count()
        )

        for i in range(await selects.count()):

            select = selects.nth(i)

            print(
                f"SELECT {i}:",
                await select.get_attribute("id"),
                await select.get_attribute("name")
            )

            options = select.locator("option")

            print(
                "  Options:",
                await options.count()
            )

            for j in range(
                min(await options.count(), 10)
            ):

                option = options.nth(j)

                print(
                    "   ",
                    j,
                    await option.inner_text(),
                    "| value =",
                    await option.get_attribute("value")
                )

        # Inputs
        inputs = page.locator("input")

        print(
            "\nInput elements:",
            await inputs.count()
        )

        for i in range(await inputs.count()):

            inp = inputs.nth(i)

            print(
                f"INPUT {i}:",
                "type=",
                await inp.get_attribute("type"),
                "id=",
                await inp.get_attribute("id"),
                "name=",
                await inp.get_attribute("name"),
                "value=",
                await inp.get_attribute("value")
            )

        # Buttons
        buttons = page.locator(
            "button, input[type='button'], "
            "input[type='submit']"
        )

        print(
            "\nButton elements:",
            await buttons.count()
        )

        for i in range(await buttons.count()):

            button = buttons.nth(i)

            print(
                f"BUTTON {i}:",
                await button.inner_text(),
                "| value=",
                await button.get_attribute("value"),
                "| id=",
                await button.get_attribute("id")
            )

        await browser.close()


async def main():

    try:

        await check_cameo()

    except Exception as error:

        print(
            "Cameo monitor error:",
            error
        )


if __name__ == "__main__":

    asyncio.run(main())
