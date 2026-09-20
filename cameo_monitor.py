import asyncio

from playwright.async_api import async_playwright


CAMEO_URL = "https://ipostatus1.cameoindia.com/"


async def main():

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

        await page.wait_for_timeout(3000)

        company = page.locator("#drpCompany")

        options = company.locator("option")

        count = await options.count()

        print(
            "Company options:",
            count
        )

        # Use the first actual company.
        option = options.nth(1)

        company_name = (
            await option.inner_text()
        ).strip()

        company_value = await option.get_attribute(
            "value"
        )

        print(
            "\nSelecting:",
            company_name
        )

        print(
            "Value:",
            company_value
        )

        # Capture network requests while the
        # company is selected.
        requests_seen = []

        def record_request(request):

            url = request.url

            if (
                "cameo" in url.lower()
                or "ipo" in url.lower()
                or "status" in url.lower()
            ):

                requests_seen.append(
                    (
                        request.method,
                        url
                    )
                )

        page.on(
            "request",
            record_request
        )

        await company.select_option(
            company_value
        )

        await page.wait_for_timeout(5000)

        print("\nRequests observed:")

        for method, url in requests_seen:

            print(
                method,
                url
            )

        # Check the Basis link.
        basis = page.get_by_text(
            "CLICK TO VIEW BASIS OF ALLOTMENT",
            exact=True
        )

        print(
            "\nBasis link count:",
            await basis.count()
        )

        if await basis.count() > 0:

            print(
                "Basis link found."
            )

            print(
                "Visible:",
                await basis.is_visible()
            )

            # Capture popup/new-page events.
            try:

                async with page.expect_popup(
                    timeout=5000
                ) as popup_info:

                    await basis.click()

                popup = await popup_info.value

                await popup.wait_for_load_state(
                    "domcontentloaded"
                )

                print(
                    "\nBasis link opened a new page."
                )

                print(
                    "Popup URL:",
                    popup.url
                )

                print(
                    "Popup title:",
                    await popup.title()
                )

                await popup.close()

            except Exception:

                print(
                    "\nBasis link did not open "
                    "a popup."
                )

                print(
                    "Checking current page URL:"
                )

                print(page.url)

        else:

            print(
                "Basis link not found."
            )

        await browser.close()


if __name__ == "__main__":

    asyncio.run(main())
