import os
import asyncio

import requests
from playwright.async_api import async_playwright


# ============================================================
# CONFIGURATION
# ============================================================

KFIN_URL = "https://ipostatus.kfintech.com/ipostatus"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "kfin_state.txt"


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
# STATE
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
            "Could not read KFin state:",
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
        "KFin state saved successfully."
    )


# ============================================================
# GET IPO OPTIONS
# ============================================================

async def get_ipos(page):

    print()
    print("=" * 60)
    print("Checking KFin IPO status page:")
    print(KFIN_URL)
    print("=" * 60)

    try:

        await page.goto(
            KFIN_URL,
            wait_until="domcontentloaded",
            timeout=30000
        )

    except Exception as error:

        print(
            "Page-load warning:",
            error
        )

    # Allow Angular/JavaScript content to load.
    await page.wait_for_timeout(5000)

    print(
        "Page title:",
        await page.title()
    )

    # --------------------------------------------------------
    # Look for select elements
    # --------------------------------------------------------

    selects = page.locator("select")

    select_count = await selects.count()

    print(
        "Select elements:",
        select_count
    )

    ipos = []

    for i in range(select_count):

        select = selects.nth(i)

        try:

            select_id = await select.get_attribute(
                "id"
            )

            select_name = await select.get_attribute(
                "name"
            )

            print(
                f"Select {i}: "
                f"id={select_id}, "
                f"name={select_name}"
            )

            options = select.locator(
                "option"
            )

            option_count = await options.count()

            print(
                "Options:",
                option_count
            )

            for j in range(option_count):

                option = options.nth(j)

                value = await option.get_attribute(
                    "value"
                )

                text = (
                    await option.inner_text()
                ).strip()

                if not text:
                    continue

                # Ignore generic placeholder options.
                lower_text = text.lower()

                if lower_text in {
                    "select ipo",
                    "select",
                    "please select",
                    "select ipo name",
                }:
                    continue

                if value is None:
                    value = ""

                print(
                    f"  {value} - {text}"
                )

                ipos.append(
                    (
                        value,
                        text
                    )
                )

        except Exception as error:

            print(
                "Could not inspect select:",
                error
            )

    # Remove duplicates while preserving values.
    unique_ipos = {}

    for value, name in ipos:

        key = f"{value}|{name}"

        unique_ipos[key] = {
            "value": value,
            "name": name,
        }

    print()
    print(
        "Unique IPO options:",
        len(unique_ipos)
    )

    for key, ipo in unique_ipos.items():

        print(
            ipo["value"],
            "-",
            ipo["name"]
        )

    return unique_ipos


# ============================================================
# MAIN MONITOR
# ============================================================

async def monitor_kfin():

    state = load_state()

    print()
    print(
        "Previously detected KFin IPOs:",
        len(state)
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        try:

            ipos = await get_ipos(
                page
            )

        finally:

            await browser.close()

    print()
    print("=" * 60)
    print("KFIN IPO SUMMARY")
    print("=" * 60)

    print(
        "Total unique IPOs:",
        len(ipos)
    )

    # --------------------------------------------------------
    # If nothing was detected, do not alter the state.
    # --------------------------------------------------------

    if not ipos:

        print()
        print(
            "No IPO options detected."
        )

        print(
            "State will not be changed."
        )

        return

    # --------------------------------------------------------
    # First run:
    #
    # Save existing IPOs as baseline.
    # --------------------------------------------------------

    if not state:

        print()
        print(
            "First KFin run detected."
        )

        print(
            "Saving current IPOs as baseline."
        )

        for key in ipos:

            state.add(key)

        save_state(state)

        print(
            "Baseline created."
        )

        print(
            "No Telegram alerts sent on first run."
        )

        return

    # --------------------------------------------------------
    # Detect new IPOs
    # --------------------------------------------------------

    new_ipos = []

    for key, ipo in ipos.items():

        if key not in state:

            new_ipos.append(
                ipo
            )

    print()
    print(
        "New KFin IPOs:",
        len(new_ipos)
    )

    # --------------------------------------------------------
    # Telegram alerts
    # --------------------------------------------------------

    for ipo in new_ipos:

        message = (
            "🚨 KFIN IPO STATUS UPDATE\n\n"
            f"IPO: {ipo['name']}\n\n"
            "This IPO has appeared in the "
            "official KFin IPO Allotment Status "
            "service.\n\n"
            f"KFin IPO status page:\n"
            f"{KFIN_URL}"
        )

        try:

            send_telegram(
                message
            )

            key = (
                f"{ipo['value']}|"
                f"{ipo['name']}"
            )

            state.add(
                key
            )

            save_state(
                state
            )

        except Exception as error:

            print()
            print(
                "Telegram error:"
            )

            print(error)

    # --------------------------------------------------------
    # Save all currently detected IPOs.
    # --------------------------------------------------------

    for key in ipos:

        state.add(key)

    save_state(state)

    print()
    print("=" * 60)
    print("KFIN MONITOR FINISHED")
    print("=" * 60)

    print(
        "New alerts:",
        len(new_ipos)
    )

    print(
        "Saved IPOs:",
        len(state)
    )


# ============================================================
# ENTRY POINT
# ============================================================

async def main():

    try:

        await monitor_kfin()

    except Exception as error:

        print()
        print(
            "KFin monitor failed:"
        )

        print(error)

        raise


if __name__ == "__main__":

    asyncio.run(main())
