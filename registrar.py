import asyncio
from playwright.async_api import async_playwright

URL = "https://in.mpms.mufg.com/Initial_Offer/public-issues.html"


async def inspect_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        await page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        print("\n--- PAGE TITLE ---")
        print(await page.title())

        print("\n--- COMPANY OPTIONS ---")

        options = await page.locator(
            "select option"
        ).all()

        for option in options:
            text = (await option.inner_text()).strip()
            value = await option.get_attribute("value")

            if "manika" in text.lower():
                print(f"Company: {text}")
                print(f"Value: {value}")

        print("\n--- FORMS ---")

        forms = await page.locator("form").all()

        for form in forms:
            action = await form.get_attribute("action")
            method = await form.get_attribute("method")

            print(f"Action: {action}")
            print(f"Method: {method}")

        print("\n--- BUTTONS ---")

        buttons = await page.locator("button").all()

        for button in buttons:
            text = (await button.inner_text()).strip()

            if text:
                print(f"Button: {text}")

        print("\n--- INPUT FIELDS ---")

        inputs = await page.locator("input").all()

        for field in inputs:
            name = await field.get_attribute("name")
            field_type = await field.get_attribute("type")

            print(f"Name: {name} | Type: {field_type}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_page())
