import os
import json
import asyncio
import requests

from playwright.async_api import async_playwright


# ============================================================
# CONFIG
# ============================================================

KFIN_URL = "https://ipostatus.kfintech.com/ipostatus"

KFIN_API = (
    "https://0uz601ms56.execute-api.ap-south-1.amazonaws.com/"
    "prod/api/query?type="
)

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", ""
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID", ""
).strip()

KFIN_PANS = os.getenv(
    "KFIN_PANS", ""
).strip()

OLD_KFIN_PAN = os.getenv(
    "KFIN_PAN", ""
).strip()

STATE_FILE = "kfin_status_state.json"


# ============================================================
# PAN LIST
# ============================================================

def get_pans():

    pans = []

    if KFIN_PANS:
        pans.extend(
            x.strip().upper()
            for x in KFIN_PANS.split(",")
            if x.strip()
        )

    if not pans and OLD_KFIN_PAN:
        pans.append(
            OLD_KFIN_PAN.upper()
        )

    # Remove duplicates
    return list(dict.fromkeys(pans))


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN:
        print("Telegram token missing.")
        return False

    if not TELEGRAM_CHAT_ID:
        print("Telegram chat ID missing.")
        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    response.raise_for_status()

    print("Telegram notification sent.")

    return True


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
        ) as f:

            data = json.load(f)

        if not isinstance(data, list):
            return set()

        return set(
            str(x)
            for x in data
        )

    except Exception as error:

        print(
            "Could not load KFin state:",
            type(error).__name__
        )

        return set()


def save_state(state):

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            sorted(state),
            f,
            indent=2
        )


# ============================================================
# MASK PAN
# ============================================================

def mask_pan(pan):

    if len(pan) != 10:
        return "**********"

    return (
        pan[:2]
        + "******"
        + pan[-2:]
    )


# ============================================================
# DISCOVER KFIN IPOs
# ============================================================

async def discover_ipos(page):

    print()
    print("=" * 60)
    print("DISCOVERING KFIN IPOs")
    print("=" * 60)

    await page.goto(
        KFIN_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    await page.wait_for_timeout(3000)

    dropdown = page.locator(
        "#ddlCompany"
    )

    if await dropdown.count() == 0:

        print(
            "KFin IPO dropdown not found."
        )

        return []

    options = dropdown.locator(
        "option"
    )

    count = await options.count()

    print(
        "KFin IPO options:",
        count
    )

    records = []

    for i in range(count):

        option = options.nth(i)

        client_id = (
            await option.get_attribute(
                "value"
            )
        )

        name = (
            await option.inner_text()
        ).strip()

        if not client_id:
            continue

        if not name:
            continue

        # Ignore placeholder entries
        if client_id in (
            "0",
            "-1"
        ):
            continue

        record = {
            "client_id": str(
                client_id
            ).strip(),
            "name": name,
        }

        records.append(record)

        print(
            f"{client_id} - {name}"
        )

    return records


# ============================================================
# KFIN PAN API
# ============================================================

def query_kfin(
    client_id,
    pan
):

    headers = {
        "reqparam": pan,
        "client_id": client_id,
        "Access-Control-Allow-Origin": "*",
        "User-Agent": "Mozilla/5.0",
    }

    try:

        response = requests.get(
            KFIN_API + "pan",
            headers=headers,
            timeout=30,
        )

        print(
            "KFin API status:",
            response.status_code,
            "| IPO:",
            client_id
        )

        if response.status_code != 200:
            return None

        return response.json()

    except Exception as error:

        print(
            "KFin API error:",
            type(error).__name__
        )

        return None


# ============================================================
# EXTRACT RESULT
# ============================================================

def extract_result(data):

    if not data:
        return None

    # API responses can be wrapped differently.
    # Look recursively for a result object/list.

    candidates = []

    if isinstance(data, dict):

        candidates.append(data)

        for key in (
            "data",
            "result",
            "results",
            "response",
            "body"
        ):

            value = data.get(key)

            if isinstance(value, dict):
                candidates.append(value)

            elif isinstance(value, list):
                candidates.extend(
                    x for x in value
                    if isinstance(x, dict)
                )

    elif isinstance(data, list):

        candidates.extend(
            x for x in data
            if isinstance(x, dict)
        )

    for item in candidates:

        if (
            "All_Shares" in item
            or "all_shares" in item
        ):

            return item

    return None


# ============================================================
# CHECK ONE IPO × ONE PAN
# ============================================================

def check_one(
    ipo,
    pan
):

    data = query_kfin(
        ipo["client_id"],
        pan
    )

    result = extract_result(data)

    if not result:

        print(
            "No allotment result:",
            ipo["name"]
        )

        return None

    all_shares = (
        result.get("All_Shares")
        if "All_Shares" in result
        else result.get("all_shares")
    )

    try:

        shares = int(
            str(all_shares or "0").strip()
        )

    except ValueError:

        shares = 0

    print(
        ipo["name"],
        "|",
        mask_pan(pan),
        "| Allotted:",
        shares
    )

    return {
        "shares": shares,
        "application": result.get(
            "Appln_No",
            ""
        ),
        "name": result.get(
            "Name",
            ""
        ),
        "dp_clid": result.get(
            "DP_CLID",
            ""
        ),
    }


# ============================================================
# MAIN
# ============================================================

async def monitor_kfin():

    pans = get_pans()

    if not pans:

        print(
            "No KFin PANs configured."
        )

        return

    print(
        "Configured PAN count:",
        len(pans)
    )

    state = load_state()

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        try:

            ipos = await discover_ipos(
                page
            )

            print()
            print(
                "Total KFin IPOs:",
                len(ipos)
            )

            for ipo in ipos:

                print()
                print(
                    "=" * 60
                )

                print(
                    "CHECKING:",
                    ipo["name"]
                )

                for pan in pans:

                    result = check_one(
                        ipo,
                        pan
                    )

                    if not result:
                        continue

                    shares = result[
                        "shares"
                    ]

                    # ------------------------------------------------
                    # ALLOTMENT FOUND
                    # ------------------------------------------------

                    if shares > 0:

                        alert_key = (
                            ipo["client_id"]
                            + "|"
                            + pan
                        )

                        if alert_key in state:

                            print(
                                "Already alerted:",
                                ipo["name"],
                                mask_pan(pan)
                            )

                            continue

                        message = (
                            "🎉 IPO ALLOTMENT FOUND\n\n"
                            f"IPO: {ipo['name']}\n"
                            "Registrar: KFintech\n\n"
                            f"PAN: {mask_pan(pan)}\n"
                            f"Shares Allotted: {shares}\n"
                        )

                        if result["application"]:

                            message += (
                                f"Application: "
                                f"{result['application']}\n"
                            )

                        message += (
                            "\n🔗 Check official KFin status:\n"
                            f"{KFIN_URL}"
                        )

                        if send_telegram(
                            message
                        ):

                            state.add(
                                alert_key
                            )

                            save_state(
                                state
                            )

        finally:

            await browser.close()

    print()
    print("=" * 60)
    print("KFIN MONITOR FINISHED")
    print("=" * 60)


if __name__ == "__main__":

    asyncio.run(
        monitor_kfin()
    )
