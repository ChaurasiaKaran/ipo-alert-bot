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

        print(
            "Company options:",
            await company.locator("option").count()
        )

        # Inspect the select element itself.
        print("\nCompany dropdown attributes:")

        for attr in [
            "id",
            "name",
            "onchange",
            "class",
            "value"
        ]:

            print(
                attr + ":",
                await company.get_attribute(attr)
            )

        # Inspect the surrounding form.
        form = company.locator(
            "xpath=ancestor::form"
        ).first

        print("\nForm information:")

        print(
            "Form count:",
            await company.locator(
                "xpath=ancestor::form"
            ).count()
        )

        if await form.count():

            print(
                "Action:",
                await form.get_attribute("action")
            )

            print(
                "Method:",
                await form.get_attribute("method")
            )

        # Inspect scripts containing the dropdown ID.
        scripts = page.locator("script")

        print(
            "\nSearching page scripts..."
        )

        for i in range(await scripts.count()):

            text = await scripts.nth(i).inner_text()

            if (
                "drpCompany" in text
                or "Basis" in text
                or "Allotment" in text
            ):

                print(
                    "\n--- SCRIPT", i, "---"
                )

                print(text[:8000])

        # Inspect the hidden Basis link.
        basis = page.get_by_text(
            "CLICK TO VIEW BASIS OF ALLOTMENT",
            exact=True
        )

        print(
            "\nBasis link count:",
            await basis.count()
        )

        if await basis.count():

            print(
                "Visible:",
                await basis.is_visible()
            )

            print(
                "Tag:",
                await basis.evaluate(
                    "(el) => el.tagName"
                )
            )

            print(
                "Outer HTML:"
            )

            print(
                await basis.evaluate(
                    "(el) => el.outerHTML"
                )
            )

        await browser.close()


if __name__ == "__main__":

    asyncio.run(main())
