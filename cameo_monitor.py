import asyncio

from playwright.async_api import async_playwright


CAMEO_URL = "https://ipostatus1.cameoindia.com/"


async def inspect_company(page, value, name):

    print("\n" + "=" * 60)
    print("Testing company:", name)
    print("Value:", value)
    print("=" * 60)

    try:

        await page.select_option(
            "#drpCompany",
            value=value
        )

        await page.wait_for_timeout(3000)

        print("Company selected successfully.")

        # Look for links
        links = page.locator("a")

        print(
            "Links after selection:",
            await links.count()
        )

        for i in range(await links.count()):

            link = links.nth(i)

            text = (
                await link.inner_text()
            ).strip()

            href = await link.get_attribute(
                "href"
            )

            if text or href:

                print(
                    f"LINK {i}:",
                    repr(text),
                    "|",
                    href
                )

        # Look for visible text related to allotment
        body = await page.locator(
            "body"
        ).inner_text()

        lines = [
            line.strip()
            for line in body.splitlines()
            if line.strip()
        ]

        print("\nRelevant text:")

        for line in lines:

            lower = line.lower()

            if (
                "allot" in lower
                or "basis" in lower
                or "ipo" in lower
                or "pdf" in lower
                or "company" in lower
            ):

                print(line)

    except Exception as error:

        print(
            "Error testing company:",
            error
        )


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print(
            "Opening Cameo IPO status portal..."
        )

        await page.goto(
            CAMEO_URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        company = page.locator(
            "#drpCompany"
        )

        options = company.locator(
            "option"
        )

        count = await options.count()

        print(
            "\nTotal company options:",
            count
        )

        # Test the first 5 real companies.
        # We intentionally don't submit any
        # personal-status form or CAPTCHA.

        tested = 0

        for i in range(1, count):

            option = options.nth(i)

            name = (
                await option.inner_text()
            ).strip()

            value = await option.get_attribute(
                "value"
            )

            if not value or value == "0":
                continue

            await inspect_company(
                page,
                value,
                name
            )

            tested += 1

            if tested >= 5:
                break

        await browser.close()


if __name__ == "__main__":

    asyncio.run(main())
