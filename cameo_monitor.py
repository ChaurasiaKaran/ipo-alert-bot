import asyncio

from playwright.async_api import async_playwright


CAMEO_URL = "https://cameoindia.com/"


async def check_cameo():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print("Opening Cameo official website...")

        await page.goto(
            CAMEO_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        print("Page title:", await page.title())

        input_count = await page.locator(
            "input"
        ).count()

        link_count = await page.locator(
            "a"
        ).count()

        button_count = await page.locator(
            "button, input[type='button'], input[type='submit']"
        ).count()

        print(
            "Input elements:",
            input_count
        )

        print(
            "Link elements:",
            link_count
        )

        print(
            "Button elements:",
            button_count
        )

        body = await page.locator(
            "body"
        ).inner_text()

        text = body.lower()

        indicators = {
            "IPO":
                "ipo" in text,

            "Allotment":
                "allotment" in text,

            "Registrar":
                "registrar" in text,

            "Investor":
                "investor" in text
        }

        print("\nCameo portal checks:")

        for name, result in indicators.items():

            print(
                f"{name}:",
                result
            )

        if (
            indicators["IPO"]
            or indicators["Allotment"]
        ):

            print(
                "\nCameo IPO-related "
                "content detected."
            )

        else:

            print(
                "\nCameo IPO structure "
                "needs further inspection."
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
