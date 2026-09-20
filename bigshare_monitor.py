import os
import asyncio
import requests

from playwright.async_api import async_playwright


TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

BIGSHARE_URL = "https://ipo.bigshareonline.com/"


def send_telegram(message):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    response.raise_for_status()

    print("Telegram notification sent.")


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

        title = await page.title()

        print("Page title:", title)

        body = await page.locator("body").inner_text()

        print("\nBigshare page loaded successfully.")

        indicators = [
            "Enter Application Number",
            "Enter PAN Number",
            "Enter Captcha",
            "SEARCH",
            "Alloted"
        ]

        found = []

        for indicator in indicators:

            if indicator.lower() in body.lower():
                found.append(indicator)

        print(
            "Detected portal elements:",
            ", ".join(found)
        )

        if len(found) >= 3:

            print(
                "Bigshare IPO allotment portal "
                "is available."
            )

        else:

            print(
                "Bigshare portal structure "
                "may have changed."
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
