import asyncio

from playwright.async_api import async_playwright


BIGSHARE_URL = "https://www.bigshareonline.com/ipo_allotment_status.aspx"


async def inspect_bigshare():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print("=" * 70)
        print("OPENING BIGSHARE IPO ALLOTMENT STATUS PAGE")
        print("=" * 70)

        await page.goto(
            BIGSHARE_URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        print()
        print("Page title:")
        print(await page.title())

        print()
        print("=" * 70)
        print("PAGE URL")
        print("=" * 70)

        print(page.url)

        print()
        print("=" * 70)
        print("COMPANY DROPDOWN")
        print("=" * 70)

        company = page.locator("#ddlCompany")

        if await company.count() > 0:

            options = company.locator("option")
            count = await options.count()

            print("Company options:", count)

            for i in range(count):

                option = options.nth(i)

                print(
                    f"{i + 1}. "
                    f"value={await option.get_attribute('value')!r} "
                    f"text={(await option.inner_text()).strip()!r}"
                )

        else:

            print(
                "Company dropdown #ddlCompany was not found."
            )

        print()
        print("=" * 70)
        print("FORM ELEMENTS")
        print("=" * 70)

        elements = page.locator(
            "input, select, button"
        )

        count = await elements.count()

        print("Total form elements:", count)

        for i in range(count):

            element = elements.nth(i)

            tag = await element.evaluate(
                "(el) => el.tagName"
            )

            print()
            print(f"ELEMENT #{i + 1}")
            print("tag:", tag)

            print(
                "id:",
                await element.get_attribute("id")
            )

            print(
                "name:",
                await element.get_attribute("name")
            )

            print(
                "type:",
                await element.get_attribute("type")
            )

            print(
                "value:",
                await element.get_attribute("value")
            )

            print(
                "placeholder:",
                await element.get_attribute("placeholder")
            )

            print(
                "onclick:",
                await element.get_attribute("onclick")
            )

        print()
        print("=" * 70)
        print("SCRIPT SOURCES")
        print("=" * 70)

        scripts = page.locator("script")

        script_count = await scripts.count()

        print(
            "Script elements:",
            script_count
        )

        for i in range(script_count):

            script = scripts.nth(i)

            src = await script.get_attribute(
                "src"
            )

            if src:

                print(
                    f"{i + 1}. EXTERNAL:",
                    src
                )

            else:

                content = await script.inner_text()

                if content.strip():

                    lower = content.lower()

                    interesting = any(
                        word in lower
                        for word in [
                            "ddlcompany",
                            "captcha",
                            "search",
                            "allot",
                            "ajax",
                            "$.ajax",
                            "fetch(",
                            "xmlhttp"
                        ]
                    )

                    if interesting:

                        print()
                        print(
                            f"{i + 1}. INLINE SCRIPT:"
                        )

                        print(
                            content[:10000]
                        )

        print()
        print("=" * 70)
        print("LINKS / BUTTONS RELATED TO ALLOTMENT")
        print("=" * 70)

        clickable = page.locator(
            "a, button, input[type='submit'], "
            "input[type='button']"
        )

        clickable_count = await clickable.count()

        for i in range(clickable_count):

            element = clickable.nth(i)

            text = (
                await element.inner_text()
            ).strip()

            value = await element.get_attribute(
                "value"
            )

            href = await element.get_attribute(
                "href"
            )

            combined = (
                text
                + " "
                + (value or "")
                + " "
                + (href or "")
            ).lower()

            if any(
                word in combined
                for word in [
                    "search",
                    "allot",
                    "result",
                    "status",
                    "captcha"
                ]
            ):

                print()
                print("TEXT:", text)
                print("VALUE:", value)
                print("HREF:", href)

        print()
        print("=" * 70)
        print("NETWORK REQUESTS DURING PAGE LOAD")
        print("=" * 70)

        requests_seen = []

        def handle_request(request):

            url = request.url

            lower = url.lower()

            if any(
                word in lower
                for word in [
                    "ipo",
                    "allot",
                    "company",
                    "status",
                    "api",
                    "ajax",
                    "captcha"
                ]
            ):

                requests_seen.append(
                    (
                        request.method,
                        url
                    )
                )

        page.on(
            "request",
            handle_request
        )

        await page.reload(
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        unique_requests = []

        for item in requests_seen:

            if item not in unique_requests:

                unique_requests.append(item)

        for method, url in unique_requests:

            print(
                method,
                url
            )

        print()
        print("=" * 70)
        print("PAGE TEXT")
        print("=" * 70)

        body_text = await page.locator(
            "body"
        ).inner_text()

        lines = [
            line.strip()
            for line in body_text.splitlines()
            if line.strip()
        ]

        for line in lines[:200]:

            print(line)

        print()
        print("=" * 70)
        print("INSPECTION FINISHED")
        print("=" * 70)

        await browser.close()


async def main():

    await inspect_bigshare()


if __name__ == "__main__":

    asyncio.run(main())
