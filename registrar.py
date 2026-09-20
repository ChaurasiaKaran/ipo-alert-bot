import asyncio
from playwright.async_api import async_playwright

URL = "https://in.mpms.mufg.com/Initial_Offer/public-issues.html"


async def inspect_allotment():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        # Log requests and responses related to allotment
        page.on(
            "request",
            lambda request: (
                print(
                    f"REQUEST: {request.method} "
                    f"{request.url}"
                )
            )
            if any(
                word in request.url.lower()
                for word in ["allot", "ipo.aspx"]
            )
            else None
        )

        page.on(
            "response",
            lambda response: (
                print(
                    f"RESPONSE: {response.status} "
                    f"{response.url}"
                )
            )
            if any(
                word in response.url.lower()
                for word in ["allot", "ipo.aspx"]
            )
            else None
        )

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        print("\n--- BASIS OF ALLOTMENT ELEMENT ---")

        links = page.locator("a")

        for i in range(await links.count()):

            link = links.nth(i)

            text = (await link.inner_text()).strip()

            if "basis" in text.lower():

                print("Text:", text)
                print(
                    "HTML:",
                    await link.evaluate(
                        "(el) => el.outerHTML"
                    )
                )

        print("\n--- CLICK BASIS OF ALLOTMENT ---")

        basis = page.get_by_text(
            "Basis Of Allotment",
            exact=True
        )

        print("Element count:", await basis.count())

        if await basis.count():

            await basis.first.click()

            await page.wait_for_timeout(3000)

            print("\n--- AFTER CLICK ---")

            print(
                (await page.locator("body").inner_text())[:10000]
            )

        await browser.close()


if __name__ == "__main__":

    asyncio.run(inspect_allotment())
