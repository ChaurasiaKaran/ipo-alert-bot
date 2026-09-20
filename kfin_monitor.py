import os
import asyncio
import requests

from playwright.async_api import async_playwright


TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

KFIN_URL = "https://ipostatus.kfintech.com/ipostatus"


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


async def check_kfin():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print("Opening KFintech IPO status page...")

        await page.goto(
            KFIN_URL,
            wait_until="networkidle",
            timeout=60000
        )

        await page.wait_for_timeout(5000)

        title = await page.title()

        print("Page title:", title)

        body = await page.locator("body").inner_text()

        print("\nKFintech page loaded successfully.")

        if "IPO Allotment Status" in body:

            print(
                "KFintech IPO allotment portal "
                "is available."
            )

        else:

            print(
                "KFintech IPO allotment page "
                "structure may have changed."
            )

        await browser.close()


async def main():

    try:

        await check_kfin()

    except Exception as error:

        print(
            "KFintech monitor error:",
            error
        )


if __name__ == "__main__":

    asyncio.run(main())
