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

        # Inspect actual controls
        select_count = await page.locator(
            "select"
        ).count()

        input_count = await page.locator(
            "input"
        ).count()

        button_count = await page.locator(
            "button, input[type='button'], input[type='submit']"
        ).count()

        print(
            "Select elements:",
            select_count
        )

        print(
            "Input elements:",
            input_count
        )

        print(
            "Button elements:",
            button_count
        )

        body = await page.locator(
            "body"
        ).inner_text()

        text = body.lower()

        checks = {
            "Company":
                "company" in text,

            "Captcha":
                "captcha" in text,

            "Basis of Allotment":
                "basis of allotment" in text,

            "IPO Status":
                "ipo status" in text
        }

        print("\nCameo IPO portal checks:")

        for name, result in checks.items():

            print(
                f"{name}:",
                result
            )

        if (
            checks["Company"]
            and checks["Captcha"]
            and checks["Basis of Allotment"]
        ):

            print(
                "\nCameo IPO status portal "
                "is available."
            )

        else:

            print(
                "\nCameo IPO portal structure "
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
