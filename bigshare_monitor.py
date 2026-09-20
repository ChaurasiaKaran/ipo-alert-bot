import asyncio

from playwright.async_api import async_playwright


SERVERS = [
    "https://ipo.bigshareonline.com/ipo_status.html",
    "https://ipo1.bigshareonline.com/ipo_status.html",
    "https://ipo2.bigshareonline.com/ipo_status.html",
]


async def inspect_server(page, url):

    print()
    print("=" * 70)
    print("CHECKING SERVER")
    print("=" * 70)
    print(url)

    try:

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

    except Exception as error:

        print()
        print("Page-load warning:")
        print(error)

    await page.wait_for_timeout(5000)

    print()
    print("Final URL:")
    print(page.url)

    print()
    print("Page title:")
    print(await page.title())

    print()
    print("-" * 70)
    print("SELECT ELEMENTS")
    print("-" * 70)

    selects = page.locator("select")

    select_count = await selects.count()

    print(
        "Total selects:",
        select_count
    )

    for i in range(select_count):

        select = selects.nth(i)

        print()
        print(
            f"SELECT #{i + 1}"
        )

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
    print("-" * 70)
    print("INPUT ELEMENTS")
    print("-" * 70)

    inputs = page.locator("input")

    input_count = await inputs.count()

    print(
        "Total inputs:",
        input_count
    )

    for i in range(input_count):

        element = inputs.nth(i)

        print()
        print(
            f"INPUT #{i + 1}"
        )

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
    print("-" * 70)
    print("BUTTONS / LINKS")
    print("-" * 70)

    elements = page.locator(
        "button, input[type='button'], "
        "input[type='submit'], a"
    )

    element_count = await elements.count()

    print(
        "Total clickable elements:",
        element_count
    )

    for i in range(element_count):

        element = elements.nth(i)

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

        combined = (
            text
            + " "
            + (value or "")
            + " "
            + (href or "")
        ).lower()

        if any(
            keyword in combined
            for keyword in [
                "search",
                "allot",
                "result",
                "status",
                "captcha",
                "company"
            ]
        ):

            print()
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
    print("-" * 70)
    print("SCRIPT SOURCES")
    print("-" * 70)

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
                f"{i + 1}. {src}"
            )

        else:

            content = await script.inner_text()

            if not content.strip():
                continue

            lower = content.lower()

            if any(
                word in lower
                for word in [
                    "company",
                    "captcha",
                    "search",
                    "allot",
                    "ajax",
                    "fetch",
                    "xmlhttp",
                    "status"
                ]
            ):

                print()
                print(
                    f"INLINE SCRIPT #{i + 1}"
                )

                print(
                    content[:12000]
                )

    print()
    print("-" * 70)
    print("PAGE TEXT")
    print("-" * 70)

    try:

        body_text = await page.locator(
            "body"
        ).inner_text()

        lines = [
            line.strip()
            for line in body_text.splitlines()
            if line.strip()
        ]

        for line in lines[:150]:

            print(line)

    except Exception as error:

        print(
            "Could not read page text:",
            error
        )


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        for server in SERVERS:

            await inspect_server(
                page,
                server
            )

        await browser.close()


if __name__ == "__main__":

    asyncio.run(main())
