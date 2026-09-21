import os
import re
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
# GET JAVASCRIPT BUNDLE URL
# ============================================================

async def get_bundle_url(page):

    scripts = await page.locator(
        "script[src]"
    ).evaluate_all(
        """
        elements => elements.map(
            element => element.src
        )
        """
    )

    for url in scripts:

        if "static/js/" in url:

            print()
            print(
                "KFin JavaScript bundle:"
            )

            print(url)

            return url

    return None


# ============================================================
# DOWNLOAD BUNDLE
# ============================================================

def download_bundle(url):

    print()
    print(
        "Downloading KFin bundle..."
    )

    response = requests.get(
        url,
        timeout=30,
        headers={
            "User-Agent":
                "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    print(
        "Bundle downloaded."
    )

    print(
        "Bundle size:",
        len(response.text)
    )

    return response.text
def find_api_types(bundle):

    print()
    print("KFin API endpoint usage:")

    patterns = [
        r'\bto\b',
        r'execute-api\.ap-south-1\.amazonaws\.com',
        r'risop\.kfintech\.com/ipostatus',
    ]

    for pattern in patterns:

        print()
        print("SEARCH:", pattern)

        matches = list(
            re.finditer(
                pattern,
                bundle,
                re.IGNORECASE
            )
        )

        print("Matches:", len(matches))

        for match in matches[:20]:

            start = max(
                0,
                match.start() - 1500
            )

            end = min(
                len(bundle),
                match.end() + 2500
            )

            print("=" * 80)
            print(bundle[start:end])
            print("=" * 80)

# ============================================================
# FIND API URLS
# ============================================================

def find_api_urls(bundle):

    urls = set(
        re.findall(
            r'https?://[^"\']+',
            bundle
        )
    )

    print()
    print("Possible KFin API URLs:")

    for url in sorted(urls):

        if "api" in url.lower() or "kfin" in url.lower():

            print(url)


# ============================================================
# EXTRACT IPO NAMES
# ============================================================

def extract_ipo_names(bundle):

    names = set()

    # --------------------------------------------------------
    # KFin's current bundle contains IPO names as JSON-style
    # strings. Look for common name fields.
    # --------------------------------------------------------

    patterns = [

        r'"(?:companyName|company_name|ipoName|ipo_name|name)"\s*:\s*"([^"]+)"',

        r'"(?:CompanyName|Company_Name|IPOName|IPO_Name)"\s*:\s*"([^"]+)"',

    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            bundle
        )

        for match in matches:

            name = match.strip()

            if not name:
                continue

            names.add(name)

    # --------------------------------------------------------
    # Also detect IPO-like uppercase strings embedded in the
    # application's data.
    # --------------------------------------------------------

    uppercase_pattern = (
        r'"([A-Z][A-Z0-9&().,\- /]{5,100}'
        r'(?:LIMITED|LTD|IPO|SME|REIT|INVIT|NCD)[^"]*)"'
    )

    try:

        matches = re.findall(
            uppercase_pattern,
            bundle
        )

        for match in matches:

            name = match.strip()

            if name:

                names.add(name)

    except Exception:
        pass

    try:

        matches = re.findall(
            uppercase_pattern,
            bundle
        )

        for match in matches:

            name = match.strip()

            if name:

                names.add(name)

    except Exception:
        pass

    # --------------------------------------------------------
    # Remove obvious non-IPO UI text.
    # --------------------------------------------------------

    excluded = {
        "SELECT IPO",
        "SELECT",
        "SUBMIT",
        "APPLICATION NO",
        "DEMAT ACCOUNT",
        "PAN",
        "ENTER PAN NO",
        "ENTER APPLICATION NO",
        "ENTER DEMAT ACCOUNT",
    }

    cleaned = set()

    for name in names:

        if name.upper() in excluded:
            continue

        if len(name) < 5:
            continue

        cleaned.add(name)

    return cleaned


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

    # --------------------------------------------------------
    # Open official KFin page
    # --------------------------------------------------------

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()
        page.on(
    "request",
    lambda request: print(
        "REQUEST:",
        request.method,
        request.url
    )
        )

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

        await page.wait_for_timeout(
            3000
        )

        print()
        print(
            "Page title:",
            await page.title()
        )

        bundle_url = await get_bundle_url(
            page
        )

        await browser.close()

    if not bundle_url:

        raise RuntimeError(
            "Could not find KFin JavaScript bundle."
        )

    # --------------------------------------------------------
    # Download and inspect bundle
    # --------------------------------------------------------

    bundle = download_bundle(
        bundle_url
    )

    ipo_names = extract_ipo_names(
        bundle
    )
    find_api_urls(
    bundle
    )
    find_api_types(
    bundle
    )

    print()
    print("=" * 60)
    print("KFIN IPO SUMMARY")
    print("=" * 60)

    print(
        "IPO names detected:",
        len(ipo_names)
    )

    for name in sorted(
        ipo_names
    ):

        print(
            name
        )

    # --------------------------------------------------------
    # Safety check
    #
    # If extraction unexpectedly finds nothing, DO NOT modify
    # the existing state.
    # --------------------------------------------------------

    if not ipo_names:

        print()
        print(
            "No IPO names detected."
        )

        print(
            "Existing state will not be changed."
        )

        return

    # --------------------------------------------------------
    # First run = baseline
    # --------------------------------------------------------

    if not state:

        print()
        print(
            "First KFin run detected."
        )

        print(
            "Saving current IPOs as baseline."
        )

        for name in ipo_names:

            state.add(name)

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

    for name in sorted(
        ipo_names
    ):

        if name not in state:

            new_ipos.append(
                name
            )

    print()
    print(
        "New KFin IPOs:",
        len(new_ipos)
    )

    # --------------------------------------------------------
    # Telegram alerts
    # --------------------------------------------------------

    for name in new_ipos:

        message = (
            "🚨 KFIN IPO STATUS UPDATE\n\n"
            f"IPO: {name}\n\n"
            "This IPO has appeared in the "
            "official KFin IPO status service.\n\n"
            f"KFin status page:\n"
            f"{KFIN_URL}"
        )

        try:

            send_telegram(
                message
            )

            state.add(
                name
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
    # Save all currently detected names
    # --------------------------------------------------------

    for name in ipo_names:

        state.add(name)

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

    asyncio.run(
        main()
    )
