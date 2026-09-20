import asyncio
from playwright.async_api import async_playwright

URL = "https://in.mpms.mufg.com/Initial_Offer/public-issues.html"

COMPANY_VALUE = "11937"


async def inspect_allotment():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        # Monitor relevant network requests
        def log_request(request):
            if "ipo.aspx" in request.url.lower():
                print(
                    f"REQUEST: {request.method} {request.url}"
                )

        def log_response(response):
            if "ipo.aspx" in response.url.lower():
                print(
                    f"RESPONSE: {response.status} "
                    f"{response.url}"
                )

        page.on("request", log_request)
        page.on("response", log_response)

        print("\n--- OPENING MUFG WEBSITE ---")

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        print("\n--- SELECTING MANIKA PLASTECH ---")

        company = page.locator("#ddlCompany")

        print(
            "Company dropdown count:",
            await company.count()
        )

        if await company.count() == 0:

            print("Company dropdown not found.")

            await browser.close()
            return

        await company.select_option(COMPANY_VALUE)

        print("Manika Plastech selected.")

        await page.wait_for_timeout(5000)

        print("\n--- BASIS OF ALLOTMENT ---")

        basis = page.locator("#basisOfAllotment")

        print(
            "Element count:",
            await basis.count()
        )

        if await basis.count():

            print(
                "Visible:",
                await basis.is_visible()
            )

            print(
                "Href:",
                await basis.get_attribute("href")
            )

            print(
                "Style:",
                await basis.get_attribute("style")
            )

            print(
                "HTML:",
                await basis.evaluate(
                    "(el) => el.outerHTML"
                )
            )

            if await basis.is_visible():

                print("Basis link is visible.")

                href = await basis.get_attribute("href")

                if href and href != "#":

                    print(
                        "Allotment URL:",
                        href
                    )

                else:

                    print(
                        "Link has no usable URL yet."
                    )

            else:

                print(
                    "Basis link is hidden. "
                    "No click attempted."
                )

        print("\n--- PAGE CONTENT ---")

        text = await page.locator("body").inner_text()

        print(text[:10000])

        await browser.close()


if __name__ == "__main__":

    asyncio.run(inspect_allotment())
