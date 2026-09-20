import os
import asyncio
from urllib.parse import urljoin

import requests
from playwright.async_api import async_playwright


# ============================================================
# CONFIGURATION
# ============================================================

CAMEO_URL = "https://ipostatus1.cameoindia.com/"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "cameo_state.txt"


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    response.raise_for_status()

    print("Telegram notification sent.")


# ============================================================
# STATE MANAGEMENT
# ============================================================

def load_state():

    if not os.path.exists(STATE_FILE):
        return set()

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return {
                line.strip()
                for line in file
                if line.strip()
            }

    except Exception as error:

        print(
            "Could not read state file:",
            error
        )

        return set()


def save_state(state):

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        for item in sorted(state):

            file.write(
                item + "\n"
            )

    print(
        "Cameo alert state saved successfully."
    )


# ============================================================
# PDF VERIFICATION
# ============================================================

def verify_pdf(url):

    print()
    print("Checking PDF availability...")
    print("PDF URL:", url)

    try:

        response = requests.get(
            url,
            timeout=30,
            allow_redirects=True,
            headers={
                "User-Agent":
                    "Mozilla/5.0 "
                    "(IPO Alert Bot)"
            },
        )

        content_type = (
            response.headers
            .get("content-type", "")
            .lower()
        )

        file_size = len(
            response.content
        )

        print(
            "HTTP status:",
            response.status_code
        )

        print(
            "Content type:",
            content_type
        )

        print(
            "File size:",
            file_size,
            "bytes"
        )

        # Some servers don't return a perfect
        # application/pdf content type, so also
        # check the PDF magic bytes.

        is_pdf_header = (
            response.content[:4]
            == b"%PDF"
        )

        is_pdf = (
            response.status_code == 200
            and (
                "application/pdf"
                in content_type
                or is_pdf_header
            )
            and file_size > 1000
        )

        return is_pdf

    except Exception as error:

        print(
            "PDF verification error:",
            error
        )

        return False


# ============================================================
# MAIN CAMEO MONITOR
# ============================================================

async def monitor_cameo():

    state = load_state()

    print(
        "Previously detected Cameo documents:",
        len(state)
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print()
        print(
            "Opening Cameo IPO status portal..."
        )

        await page.goto(
            CAMEO_URL,
            wait_until="networkidle",
            timeout=60000,
        )

        await page.wait_for_timeout(3000)

        company_dropdown = page.locator(
            "#drpCompany"
        )

        option_count = await company_dropdown.locator(
            "option"
        ).count()

        print(
            "Company options:",
            option_count
        )

        new_alerts = 0

        # ----------------------------------------------------
        # Scan every company currently listed
        # ----------------------------------------------------

        for index in range(option_count):

            option = company_dropdown.locator(
                "option"
            ).nth(index)

            value = await option.get_attribute(
                "value"
            )

            company_name = (
                await option.inner_text()
            ).strip()

            # Ignore placeholder
            if (
                not value
                or value == "0"
            ):
                continue

            print()
            print(
                "Checking:",
                company_name
            )

            print(
                "Company code:",
                value
            )

            try:

                # Select company.
                await company_dropdown.select_option(
                    value=value
                )

                # Execute the exact JavaScript
                # used by Cameo.
                await page.evaluate(
                    "GetMaster1Details()"
                )

                await page.wait_for_timeout(
                    300
                )

                basis_button = page.locator(
                    "#view_button"
                )

                if await basis_button.count() == 0:

                    print(
                        "Basis button not present."
                    )

                    continue

                display = await basis_button.evaluate(
                    "(el) => getComputedStyle(el).display"
                )

                href = await basis_button.get_attribute(
                    "href"
                )

                print(
                    "Basis button display:",
                    display
                )

                print(
                    "Basis href:",
                    href
                )

                # No published document.
                if (
                    display == "none"
                    or not href
                ):

                    print(
                        "No Basis of Allotment "
                        "document detected."
                    )

                    continue

                # Convert relative URL to absolute.
                pdf_url = urljoin(
                    CAMEO_URL,
                    href
                )

                print(
                    "Basis of Allotment detected!"
                )

                print(
                    "PDF URL:",
                    pdf_url
                )

                # ------------------------------------------------
                # Verify actual PDF
                # ------------------------------------------------

                if not verify_pdf(
                    pdf_url
                ):

                    print(
                        "Link found, but PDF "
                        "verification failed."
                    )

                    continue

                print(
                    "Official Basis of "
                    "Allotment PDF verified."
                )

                # ------------------------------------------------
                # Duplicate protection
                # ------------------------------------------------

                state_key = (
                    f"{value}|{pdf_url}"
                )

                if state_key in state:

                    print(
                        "Already alerted previously."
                    )

                    continue

                # ------------------------------------------------
                # Telegram alert
                # ------------------------------------------------

                message = (
                    "🚨 CAMEO IPO ALLOTMENT UPDATE\n\n"
                    f"IPO: {company_name}\n\n"
                    "Basis of Allotment has been "
                    "published on the official "
                    "Cameo portal.\n\n"
                    f"Official PDF:\n{pdf_url}"
                )

                send_telegram(
                    message
                )

                # Save immediately so that even
                # if a later company fails, this
                # alert won't be repeated.

                state.add(
                    state_key
                )

                save_state(
                    state
                )

                new_alerts += 1

            except Exception as error:

                print(
                    f"Error checking {company_name}:",
                    error
                )

                # Continue with the next IPO
                # instead of stopping the entire job.
                continue

        await browser.close()

    print()
    print("=" * 60)
    print(
        "CAMEO MONITOR FINISHED"
    )
    print(
        "New alerts:",
        new_alerts
    )
    print(
        "Total saved alerts:",
        len(state)
    )
    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

async def main():

    try:

        await monitor_cameo()

    except Exception as error:

        print()
        print(
            "Cameo monitor failed:"
        )

        print(error)

        raise


if __name__ == "__main__":

    asyncio.run(main())
