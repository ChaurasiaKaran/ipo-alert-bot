import asyncio
from playwright.async_api import async_playwright

URL = "https://in.mpms.mufg.com/Initial_Offer/public-issues.html"


async def inspect_form():

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

        # Select Manika Plastech
        await page.locator(
            'option[value="11937"]'
        ).locator("xpath=..").select_option("11937")

        await page.wait_for_timeout(2000)

        print("\n--- RADIO OPTIONS ---")

        radios = page.locator(
            'input[type="radio"]'
        )

        for i in range(await radios.count()):

            radio = radios.nth(i)

            print(
                "Radio:",
                i,
                "| ID:",
                await radio.get_attribute("id"),
                "| Value:",
                await radio.get_attribute("value"),
                "| Checked:",
                await radio.is_checked()
            )

        print("\n--- BUTTON DETAILS ---")

        button = page.locator("#btnsearc")

        print("Button count:", await button.count())

        if await button.count():

            print(
                "Button HTML:",
                await button.evaluate(
                    "(el) => el.outerHTML"
                )
            )

        print("\n--- CAPTCHA DETAILS ---")

        captcha = page.locator("#txtCaptch")

        print(
            "CAPTCHA HTML:",
            await captcha.evaluate(
                "(el) => el.outerHTML"
            )
        )

        print("\n--- HIDDEN FIELDS ---")

        hidden = page.locator(
            'input[type="hidden"]'
        )

        for i in range(await hidden.count()):

            field = hidden.nth(i)

            print(
                "Hidden:",
                i,
                "| ID:",
                await field.get_attribute("id"),
                "| Value:",
                await field.get_attribute("value")
            )

        await browser.close()


if __name__ == "__main__":

    asyncio.run(inspect_form())
