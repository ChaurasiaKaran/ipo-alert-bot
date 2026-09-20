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

        input_count = await page.locator(
            "input"
        ).count()

        select_count = await page.locator(
            "select"
        ).count()

        button_count = await page.locator(
            "button, input[type='button'], input[type='submit']"
        ).count()

        captcha_count = await page.get_by_text(
            "Enter Captcha",
            exact=False
        ).count()

        search_count = await page.get_by_text(
            "SEARCH",
            exact=False
        ).count()

        print(
            "Input elements:",
            input_count
        )

        print(
            "Select elements:",
            select_count
        )

        print(
            "Button elements:",
            button_count
        )

        print(
            "Captcha indicator:",
            captcha_count > 0
        )

        print(
            "Search indicator:",
            search_count > 0
        )

        if (
            input_count > 0
            and select_count > 0
            and captcha_count > 0
            and search_count > 0
        ):

            print(
                "\nBigshare IPO allotment "
                "portal is available."
            )

        else:

            print(
                "\nBigshare portal structure "
                "needs inspection."
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
