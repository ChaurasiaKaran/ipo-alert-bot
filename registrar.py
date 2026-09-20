import os
import asyncio
import requests
from pathlib import Path

from playwright.async_api import async_playwright


TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

BASE_URL = "https://in.mpms.mufg.com"

URL = (
    "https://in.mpms.mufg.com/"
    "Initial_Offer/public-issues.html"
)

COMPANY_VALUE = "11937"

STATE_FILE = Path("manika_state.txt")


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


def already_alerted(pdf_url):

    if not STATE_FILE.exists():
        return False

    previous = STATE_FILE.read_text(
        encoding="utf-8"
    ).strip()

    return previous == pdf_url


def save_state(pdf_url):

    STATE_FILE.write_text(
        pdf_url,
        encoding="utf-8"
    )


async def get_pdf_url():

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

        company = page.locator("#ddlCompany")

        await company.select_option(
            COMPANY_VALUE
        )

        await page.wait_for_timeout(5000)

        basis = page.locator(
            "#basisOfAllotment"
        )

        if await basis.count() == 0:

            print(
                "Basis of Allotment element "
                "not found."
            )

            await browser.close()

            return None

        href = await basis.get_attribute(
            "href"
        )

        visible = await basis.is_visible()

        print("Visible:", visible)
        print("PDF path:", href)

        await browser.close()

        if visible and href and href != "#":

            return BASE_URL + href

        return None


def check_pdf(pdf_url):

    print("\nChecking PDF availability...")

    response = requests.get(
        pdf_url,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    print(
        "HTTP status:",
        response.status_code
    )

    content_type = response.headers.get(
        "Content-Type",
        ""
    ).lower()

    print(
        "Content type:",
        content_type
    )

    print(
        "File size:",
        len(response.content),
        "bytes"
    )

    if response.status_code != 200:
        return False

    if "pdf" not in content_type:
        return False

    if not response.content.startswith(b"%PDF"):
        return False

    return True


async def main():

    pdf_url = await get_pdf_url()

    if not pdf_url:

        print(
            "Basis of Allotment PDF "
            "is not available."
        )

        return

    print("\nPDF URL:")
    print(pdf_url)

    available = check_pdf(pdf_url)

    if not available:

        print(
            "PDF is not available yet."
        )

        return

    print(
        "\nOfficial Basis of Allotment "
        "PDF detected."
    )

    if already_alerted(pdf_url):

        print(
            "Already alerted previously. "
            "No Telegram message sent."
        )

        return

    message = (
        "🚨 IPO ALLOTMENT DOCUMENT PUBLISHED\n\n"
        "IPO: Manika Plastech Limited\n"
        "Registrar: MUFG Intime\n\n"
        "The official Basis of Allotment "
        "PDF is now available.\n\n"
        "This confirms publication of the "
        "official allotment document; it "
        "does not by itself confirm your "
        "individual allotment.\n\n"
        f"🔗 {pdf_url}"
    )

    send_telegram(message)

    save_state(pdf_url)

    print(
        "Alert state saved successfully."
    )


if __name__ == "__main__":

    asyncio.run(main())
