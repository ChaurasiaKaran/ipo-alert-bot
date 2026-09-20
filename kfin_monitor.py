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
# EXTRACT JAVASCRIPT BUNDLES
# ============================================================

async def get_script_urls(page):

    scripts = await page.locator(
        "script[src]"
    ).evaluate_all(
        """
        elements => elements.map(
            element => element.src
        )
        """
    )

    unique = []

    for url in scripts:

        if url not in unique:

            unique.append(url)

    print()
    print(
        "JavaScript bundles found:",
        len(unique)
    )

    for url in unique:

        print(url)

    return unique


# ============================================================
# DOWNLOAD BUNDLES
# ============================================================

def download_bundle(url):

    try:

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
            "Downloaded bundle:",
            url,
            "size:",
            len(response.text)
        )

        return response.text

    except Exception as error:

        print(
            "Could not download:",
            url
        )

        print(error)

        return ""


# ============================================================
# FIND POSSIBLE KFIN API URLS
# ============================================================

def find_api_urls(bundle):

    patterns = [

        r'https?://[^"\']+',

        r'["\']([^"\']*?/prod/api/[^"\']*)["\']',

        r'["\']([^"\']*?/api/[^"\']*)["\']',

    ]

    found = set()

    for pattern in patterns:

        try:

            matches = re.findall(
                pattern,
                bundle
            )

            for match in matches:

                if isinstance(match, tuple):

                    for item in match:

                        if item:
                            found.add(item)

                else:

                    found.add(match)

        except Exception:
            continue

    # Only retain useful-looking API references.
    useful = []

    for item in found:

        lower = item.lower()

        if (
            "/api/" in lower
            or "ipo" in lower
            or "query" in lower
            or "company" in lower
        ):

            useful.append(item)

    return sorted(
        set(useful)
    )


# ============================================================
# FIND COMPANY / IPO DATA STRINGS
# ============================================================

def find_company_like_strings(bundle):

    results = set()

    # Look for common JSON/object field names.
    patterns = [

        r'"(?:companyName|company_name|ipoName|ipo_name|name)"\s*:\s*"([^"]+)"',

        r'"(?:CompanyName|Company_Name|IPOName|IPO_Name)"\s*:\s*"([^"]+)"',

    ]

    for pattern in patterns:

        try:

            matches = re.findall(
                pattern,
                bundle
            )

            for match in matches:

                text = match.strip()

                if len(text) < 3:
                    continue

                lower = text.lower()

                # Avoid generic UI strings.
                if lower in {
                    "select ipo",
                    "select",
                    "submit",
                    "pan",
                    "application no",
                    "demat account",
                }:
                    continue

                results.add(text)

        except Exception:
            continue

    return sorted(
        results
    )


# ============================================================
# MAIN INSPECTION
# ============================================================

async def inspect_kfin():

    print()
    print("=" * 60)
    print("KFINTECH SPA INSPECTION")
    print("=" * 60)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

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
            5000
        )

        print()
        print(
            "Page title:",
            await page.title()
        )

        print()
        print(
            "Visible page text:"
        )

        try:

            text = (
                await page.locator(
                    "body"
                ).inner_text()
            )

            print(
                text[:5000]
            )

        except Exception as error:

            print(
                "Could not read page text:",
                error
            )

        script_urls = await get_script_urls(
            page
        )

        await browser.close()

    # --------------------------------------------------------
    # Inspect bundles
    # --------------------------------------------------------

    all_api_urls = set()
    all_company_names = set()

    print()
    print("=" * 60)
    print("INSPECTING JAVASCRIPT BUNDLES")
    print("=" * 60)

    for url in script_urls:

        bundle = download_bundle(
            url
        )

        if not bundle:
            continue

        api_urls = find_api_urls(
            bundle
        )

        company_names = (
            find_company_like_strings(
                bundle
            )
        )

        for item in api_urls:

            all_api_urls.add(
                item
            )

        for item in company_names:

            all_company_names.add(
                item
            )

    # --------------------------------------------------------
    # Print API references
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("KFIN API REFERENCES FOUND")
    print("=" * 60)

    if all_api_urls:

        for url in sorted(
            all_api_urls
        ):

            print(url)

    else:

        print(
            "No API references found."
        )

    # --------------------------------------------------------
    # Print company-like strings
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("KFIN COMPANY-LIKE STRINGS")
    print("=" * 60)

    if all_company_names:

        for name in sorted(
            all_company_names
        ):

            print(name)

    else:

        print(
            "No company names found "
            "inside the bundles."
        )

    print()
    print("=" * 60)
    print("KFIN INSPECTION FINISHED")
    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

async def main():

    try:

        await inspect_kfin()

    except Exception as error:

        print()
        print(
            "KFin inspection failed:"
        )

        print(error)

        raise


if __name__ == "__main__":

    asyncio.run(
        main()
    )
