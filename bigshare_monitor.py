import os
import asyncio

from playwright.async_api import async_playwright


BIGSHARE_URL = "https://ipo.bigshareonline.com/"


async def check_bigshare():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print("Opening Bigshare IPO status page...")

        await page.goto(
            BIGSHARE_URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        print("Page title:", await page.title())

        # Check actual form controls rather than
        # relying on exact visible text.

        select_count = await page.locator(
            "select"
        ).count()

        input_count = await page.locator(
            "input"
        ).count()

        button_count = await page.locator(
            "button, input[type='button'], "
            "input[type='submit']"
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

        checks = {
            "Application Number":
                "application" in body.lower(),

            "PAN":
                "pan" in body.lower(),

            "Captcha":
                "captcha" in body.lower(),

            "Search":
                "search" in body.lower(),

            "Alloted":
                "alloted" in body.lower()
        }

        print("\nBigshare portal checks:")

        for name, result in checks.items():

            print(
                f"{name}:",
                result
            )

        if (
            checks["Application Number"]
            and checks["PAN"]
            and checks["Captcha"]
            and checks["Search"]
        ):

            print(
                "\nBigshare IPO allotment "
                "portal is available."
            )

        else:

            print(
                "\nBigshare portal structure "
                "needs further inspection."
            )

        await browser.close()


async def main():

    try:

        await check_bigshare()

    except Exception as error:

        print(
            "Bigshare monitor error:",
            error
        )


if __name__ == "__main__":

    asyncio.run(main())
