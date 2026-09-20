import os
import asyncio

import requests
from playwright.async_api import async_playwright


# ============================================================
# CONFIGURATION
# ============================================================

BIGSHARE_SERVERS = [
    "https://ipo.bigshareonline.com/ipo_status.html",
    "https://ipo1.bigshareonline.com/ipo_status.html",
    "https://ipo2.bigshareonline.com/ipo_status.html",
]

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "bigshare_state.txt"


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
            "Could not read Bigshare state:",
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
        "Bigshare state saved successfully."
    )


# ============================================================
# CHECK ONE BIGSHARE SERVER
# ============================================================

async def get_companies(page, server):

    print()
    print("=" * 60)
    print("Checking Bigshare server:")
    print(server)
    print("=" * 60)

    try:

        await page.goto(
            server,
            wait_until="domcontentloaded",
            timeout=30000
        )

    except Exception as error:

        print(
            "Page-load warning:",
            error
        )

    await page.wait_for_timeout(5000)

    company_dropdown = page.locator(
        "#ddlCompany"
    )

    if await company_dropdown.count() == 0:

        print(
            "Company dropdown not found."
        )

        return []

    options = company_dropdown.locator(
        "option"
    )

    option_count = await options.count()

    print(
        "Company options:",
        option_count
    )

    companies = []

    for i in range(option_count):

        option = options.nth(i)

        value = await option.get_attribute(
            "value"
        )

        name = (
            await option.inner_text()
        ).strip()

        if not value:
            continue

        if not name:
            continue

        company = (
            value,
            name
        )

        companies.append(
            company
        )

        print(
            f"{value} - {name}"
        )

    return companies


# ============================================================
# MAIN MONITOR
# ============================================================

async def monitor_bigshare():

    state = load_state()

    print()
    print(
        "Previously detected Bigshare companies:",
        len(state)
    )

    all_companies = {}

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        for server in BIGSHARE_SERVERS:

            try:

                companies = await get_companies(
                    page,
                    server
                )

                for value, name in companies:

                    key = f"{value}|{name}"

                    all_companies[key] = {
                        "value": value,
                        "name": name,
                        "server": server,
                    }

            except Exception as error:

                print()
                print(
                    "Error checking server:"
                )

                print(server)

                print(error)

                continue

        await browser.close()

    print()
    print("=" * 60)
    print("BIGSHARE COMPANY SUMMARY")
    print("=" * 60)

    for key, company in sorted(
        all_companies.items()
    ):

        print(
            company["value"],
            "-",
            company["name"]
        )

    print()
    print(
        "Total unique companies:",
        len(all_companies)
    )

    # --------------------------------------------------------
    # First run:
    #
    # Save currently visible companies without sending
    # alerts. This prevents Telegram from immediately sending
    # alerts for all companies that already existed before the
    # monitor was installed.
    # --------------------------------------------------------

    if not state:

        print()
        print(
            "First Bigshare run detected."
        )

        print(
            "Saving current companies as baseline."
        )

        for key in all_companies:

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
    # Detect new companies
    # --------------------------------------------------------

    new_companies = []

    for key, company in all_companies.items():

        if key not in state:

            new_companies.append(
                company
            )

    print()
    print(
        "New Bigshare companies:",
        len(new_companies)
    )

    # --------------------------------------------------------
    # Telegram alerts
    # --------------------------------------------------------

    for company in new_companies:

        message = (
            "🚨 BIGSHARE IPO STATUS UPDATE\n\n"
            f"IPO: {company['name']}\n\n"
            "This IPO has appeared in the "
            "official Bigshare IPO Allotment "
            "Status company list.\n\n"
            f"Bigshare status page:\n"
            f"{company['server']}"
        )

        try:

            send_telegram(
                message
            )

            state.add(
                f"{company['value']}|{company['name']}"
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
    # Save state
    # --------------------------------------------------------

    for key in all_companies:

        state.add(key)

    save_state(state)

    print()
    print("=" * 60)
    print("BIGSHARE MONITOR FINISHED")
    print("=" * 60)

    print(
        "New alerts:",
        len(new_companies)
    )

    print(
        "Saved companies:",
        len(state)
    )


# ============================================================
# ENTRY POINT
# ============================================================

async def main():

    try:

        await monitor_bigshare()

    except Exception as error:

        print()
        print(
            "Bigshare monitor failed:"
        )

        print(error)

        raise


if __name__ == "__main__":

    asyncio.run(main())
