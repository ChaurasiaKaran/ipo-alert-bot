import asyncio

from playwright.async_api import async_playwright


BIGSHARE_URL = "https://ipo.bigshareonline.com/"


async def inspect_bigshare():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print("=" * 70)
        print("OPENING BIGSHARE IPO STATUS PAGE")
        print("=" * 70)

        await page.goto(
            BIGSHARE_URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        print()
        print("Page title:")
        print(await page.title())

        print()
        print("=" * 70)
        print("SELECT ELEMENTS")
        print("=" * 70)

        selects = page.locator("select")

        select_count = await selects.count()

        print("Total selects:", select_count)

        for i in range(select_count):

            select = selects.nth(i)

            print()
            print(f"SELECT #{i + 1}")

            print(
                "id:",
                await select.get_attribute("id")
            )

            print(
                "name:",
                await select.get_attribute("name")
            )

            options = select.locator("option")

            option_count = await options.count()

            print(
                "options:",
                option_count
            )

            for j in range(
                min(option_count, 50)
            ):

                option = options.nth(j)

                value = await option.get_attribute(
                    "value"
                )

                text = (
                    await option.inner_text()
                ).strip()

                print(
                    f"  {j + 1}. "
                    f"value={value!r} "
                    f"text={text!r}"
                )

        print()
        print("=" * 70)
        print("INPUT ELEMENTS")
        print("=" * 70)

        inputs = page.locator("input")

        input_count = await inputs.count()

        print(
            "Total inputs:",
            input_count
        )

        for i in range(input_count):

            element = inputs.nth(i)

            print()
            print(f"INPUT #{i + 1}")

            print(
                "type:",
                await element.get_attribute("type")
            )

            print(
                "id:",
                await element.get_attribute("id")
            )

            print(
                "name:",
                await element.get_attribute("name")
            )

            print(
                "placeholder:",
                await element.get_attribute(
                    "placeholder"
                )
            )

        print()
        print("=" * 70)
        print("BUTTONS")
        print("=" * 70)

        buttons = page.locator(
            "button, input[type='button'], "
            "input[type='submit'], a"
        )

        button_count = await buttons.count()

        print(
            "Total button/link elements:",
            button_count
        )

        for i in range(button_count):

            element = buttons.nth(i)

            text = (
                await element.inner_text()
            ).strip()

            value = await element.get_attribute(
                "value"
            )

            href = await element.get_attribute(
                "href"
            )

            element_id = await element.get_attribute(
                "id"
            )

            if (
                text
                or value
                or href
            ):

                print()

                print(
                    f"ELEMENT #{i + 1}"
                )

                print(
                    "tag:",
                    await element.evaluate(
                        "(el) => el.tagName"
                    )
                )

                print(
                    "id:",
                    element_id
                )

                print(
                    "text:",
                    text
                )

                print(
                    "value:",
                    value
                )

                print(
                    "href:",
                    href
                )

        print()
        print("=" * 70)
        print("IMPORTANT PAGE TEXT")
        print("=" * 70)

        body_text = await page.locator(
            "body"
        ).inner_text()

        lines = [
            line.strip()
            for line in body_text.splitlines()
            if line.strip()
        ]

        keywords = [
            "allot",
            "basis",
            "ipo",
            "status",
            "company",
            "captcha",
            "application",
            "pan",
            "search",
            "download",
            "result"
        ]

        found_lines = []

        for line in lines:

            lower_line = line.lower()

            if any(
                keyword in lower_line
                for keyword in keywords
            ):

                if line not in found_lines:

                    found_lines.append(line)

        for line in found_lines[:150]:

            print(line)

        print()
        print("=" * 70)
        print("LINKS CONTAINING IMPORTANT KEYWORDS")
        print("=" * 70)

        links = page.locator("a")

        link_count = await links.count()

        for i in range(link_count):

            link = links.nth(i)

            text = (
                await link.inner_text()
            ).strip()

            href = await link.get_attribute(
                "href"
            )

            combined = (
                f"{text} {href
