import os
import re
import asyncio
import time
import json
import requests

from playwright.async_api import async_playwright


# ============================================================
# CONFIGURATION
# ============================================================

KFIN_URL = "https://ipostatus.kfintech.com/ipostatus"

KFIN_API = (
    "https://0uz601ms56.execute-api.ap-south-1.amazonaws.com/"
    "prod/api/query?type="
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Multiple PANs:
#
# KFIN_PANS=ABCDE1234F,XYZAB5678C,PQRST9012D
#
# Existing KFIN_PAN is also supported as a fallback.
#
KFIN_PANS = os.getenv("KFIN_PANS", "").strip()
OLD_KFIN_PAN = os.getenv("KFIN_PAN", "").strip()

# Number of recent IPOs to check.
#
# Keeping this limited avoids sending a very large number
# of requests to KFin on every GitHub Actions run.
#
MAX_IPOS_TO_CHECK = int(
    os.getenv("KFIN_MAX_IPOS", "5")
)

STATE_FILE = "kfin_state.txt"
STATUS_STATE_FILE = "kfin_status_state.json"


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials are not configured.")
        return

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=30,
        )

        if response.status_code == 200:
            print("Telegram alert sent.")
        else:
            print(
                "Telegram error:",
                response.status_code
            )

    except requests.RequestException as e:

        print(
            "Telegram request failed:",
            type(e).__name__
        )


# ============================================================
# IPO DISCOVERY STATE
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

            return {
                line.strip()
                for line in f
                if line.strip()
            }

    except Exception as e:

        print(
            "Could not read KFin state:",
            type(e).__name__
        )

        return set()


def save_state(ipo_names):

    try:

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            for name in sorted(ipo_names):
                f.write(name + "\n")

        print("KFin IPO state saved successfully.")

    except Exception as e:

        print(
            "Could not save KFin state:",
            type(e).__name__
        )


# ============================================================
# ALLOTMENT STATUS STATE
# ============================================================

def load_status_state():

    if not os.path.exists(STATUS_STATE_FILE):
        return {}

    try:

        with open(
            STATUS_STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, dict):
                return data

    except Exception as e:

        print(
            "Could not read KFin status state:",
            type(e).__name__
        )

    return {}


def save_status_state(state):

    try:

        with open(
            STATUS_STATE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                state,
                f,
                indent=2,
                sort_keys=True
            )

        print("KFin allotment state saved successfully.")

    except Exception as e:

        print(
            "Could not save KFin status state:",
            type(e).__name__
        )


# ============================================================
# PAN HANDLING
# ============================================================

def get_kfin_pans():

    """
    Read multiple PANs from:

        KFIN_PANS

    Example:

        ABCDE1234F,XYZAB5678C,PQRST9012D

    KFIN_PAN remains supported as a fallback.
    """

    raw = KFIN_PANS

    if not raw:
        raw = OLD_KFIN_PAN

    if not raw:

        print(
            "No KFin PAN secret configured."
        )

        return []

    pans = []

    for value in raw.split(","):

        pan = value.strip().upper()

        if re.fullmatch(
            r"[A-Z]{5}[0-9]{4}[A-Z]",
            pan
        ):

            if pan not in pans:
                pans.append(pan)

        else:

            print(
                "Ignoring an invalid PAN entry."
            )

    print(
        "KFin PANs configured:",
        len(pans)
    )

    return pans


def mask_pan(pan):

    """
    Example:

        ABCDE1234F
        XXXXX1234F
    """

    if len(pan) != 10:
        return "XXXXX"

    return "XXXXX" + pan[5:]


# ============================================================
# KFIN BUNDLE
# ============================================================

def get_bundle_url(page):

    scripts = await page.locator(
        "script[src]"
    ).evaluate_all(
        """
        scripts => scripts.map(s => s.src)
        """
    )

    for url in scripts:

        if "static/js/" in url:

            return url

    return None


def download_bundle(url):

    print()
    print("Downloading KFin bundle...")

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=30,
        )

        response.raise_for_status()

        print("Bundle downloaded.")

        print(
            "Bundle size:",
            len(response.text)
        )

        return response.text

    except requests.RequestException as e:

        print(
            "Could not download KFin bundle:",
            type(e).__name__
        )

        return ""


# ============================================================
# IPO EXTRACTION
# ============================================================

def extract_ipo_records(bundle):

    """
    Extract:

        clientId
        name

    from KFin's embedded IPO list.
    """

    pattern = (
        r'\{"clientId":"([^"]+)","name":"([^"]+)"\}'
    )

    matches = re.findall(
        pattern,
        bundle
    )

    records = []

    seen_ids = set()

    for client_id, name in matches:

        if client_id in seen_ids:
            continue

        seen_ids.add(client_id)

        records.append({
            "client_id": client_id,
            "name": name,
        })

    return records


def extract_ipo_names(bundle):

    records = extract_ipo_records(bundle)

    return {
        record["name"]
        for record in records
    }


# ============================================================
# API / JAVASCRIPT INSPECTION
# ============================================================

def find_api_urls(bundle):

    print()
    print("KFin API references:")
    print("=" * 80)

    urls = re.findall(
        r'https?://[^"\']+',
        bundle
    )

    seen = set()

    for url in urls:

        if (
            "execute-api" in url
            or "ris.kfintech" in url
            or "risop.kfintech" in url
        ):

            if url not in seen:

                print(url)

                seen.add(url)


def find_submit_logic(bundle):

    print()
    print("KFin request construction:")
    print("=" * 80)

    searches = [
        "e=I(),t=e.type,n=e.header",
        "reqparam",
        "client_id",
        "api/query?type=",
    ]

    for keyword in searches:

        count = len(
            re.findall(
                re.escape(keyword),
                bundle,
                re.IGNORECASE
            )
        )

        print(
            f"{keyword}: {count} match(es)"
        )


# ============================================================
# KFIN PAN API
# ============================================================

def query_kfin_pan(
    ipo_client_id,
    pan
):

    """
    Query KFin using PAN.

    Important:
    The PAN is never printed.
    """

    url = KFIN_API + "pan"

    headers = {
        "reqparam": pan,
        "client_id": ipo_client_id,
        "Access-Control-Allow-Origin": "*",
        "User-Agent": "Mozilla/5.0",
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30,
        )

        print(
            "KFin API HTTP status:",
            response.status_code
        )

        if response.status_code == 404:

            return {
                "status": "not_found",
                "results": []
            }

        if response.status_code == 429:

            return {
                "status": "rate_limited",
                "results": []
            }

        if response.status_code in (
            500,
            502,
            504,
        ):

            return {
                "status": "server_error",
                "results": []
            }

        if response.status_code != 200:

            return {
                "status": "error",
                "http_status": response.status_code,
                "results": []
            }

        try:

            data = response.json()

        except ValueError:

            print(
                "KFin returned a non-JSON response."
            )

            return {
                "status": "invalid_response",
                "results": []
            }

        rows = []

        if isinstance(data, dict):

            outer = data.get("data")

            if isinstance(outer, dict):

                rows = outer.get(
                    "data",
                    []
                )

            elif isinstance(outer, list):

                rows = outer

        if not isinstance(rows, list):

            rows = []

        results = []

        for row in rows:

            if not isinstance(row, dict):
                continue

            all_shares = row.get(
                "All_Shares",
                0
            )

            app_shares = row.get(
                "App_Shares",
                0
            )

            ipo_title = row.get(
                "ipoTitle"
            )

            try:

                all_shares = int(
                    all_shares or 0
                )

            except (
                TypeError,
                ValueError
            ):

                all_shares = 0

            try:

                app_shares = int(
                    app_shares or 0
                )

            except (
                TypeError,
                ValueError
            ):

                app_shares = 0

            if all_shares > 0:

                status = "Allotted"

            else:

                status = "Not Allotted"

            results.append({
                "ipo_title": ipo_title,
                "all_shares": all_shares,
                "app_shares": app_shares,
                "status": status,
            })

        return {
            "status": "success",
            "results": results
        }

    except requests.RequestException as e:

        print(
            "KFin API request failed:",
            type(e).__name__
        )

        return {
            "status": "request_error",
            "results": []
        }


# ============================================================
# ALLOTMENT CHECK
# ============================================================

def check_allotment_status(
    ipo_records,
    pans
):

    if not pans:

        print(
            "No PANs available for allotment checks."
        )

        return

    if not ipo_records:

        print(
            "No IPOs available for allotment checks."
        )

        return

    print()
    print("=" * 80)
    print("KFIN ALLOTMENT STATUS CHECK")
    print("=" * 80)

    print(
        "PANs to check:",
        len(pans)
    )

    print(
        "IPOs to check:",
        len(ipo_records)
    )

    status_state = load_status_state()

    for ipo in ipo_records:

        ipo_name = ipo["name"]
        client_id = ipo["client_id"]

        print()
        print(
            "Checking IPO:",
            ipo_name
        )

        for pan in pans:

            masked_pan = mask_pan(pan)

            print(
                "Checking PAN:",
                masked_pan
            )

            result = query_kfin_pan(
                client_id,
                pan
            )

            result_status = result.get(
                "status"
            )

            if result_status == "rate_limited":

                print(
                    "KFin rate limit reached."
                )

                print(
                    "Stopping further checks for this run."
                )

                save_status_state(
                    status_state
                )

                return

            if result_status != "success":

                print(
                    "No usable result for:",
                    masked_pan
                )

                # Small delay before next request
                time.sleep(2)

                continue

            results = result.get(
                "results",
                []
            )

            if not results:

                print(
                    "No allotment result returned."
                )

                time.sleep(2)

                continue

            for row in results:

                status = row.get(
                    "status",
                    "Unknown"
                )

                shares = row.get(
                    "all_shares",
                    0
                )

                applied = row.get(
                    "app_shares",
                    0
                )

                title = (
                    row.get("ipo_title")
                    or ipo_name
                )

                print(
                    f"Result: {status} | "
                    f"Shares: {shares} | "
                    f"Applied: {applied}"
                )

                # Unique state key for this PAN + IPO
                state_key = (
                    f"{masked_pan}|"
                    f"{client_id}"
                )

                previous = status_state.get(
                    state_key
                )

                current_record = {
                    "status": status,
                    "shares": shares,
                    "applied": applied,
                    "ipo": title,
                }

                # Alert only when the status changes
                # or when this is the first successful result.
                should_alert = (
                    previous != current_record
                )

                if should_alert:

                    message = (
                        "KFintech Allotment Update\n\n"
                        f"IPO: {title}\n"
                        f"PAN: {masked_pan}\n"
                        f"Status: {status}\n"
                        f"Allotted Shares: {shares}\n"
                        f"Applied Shares: {applied}"
                    )

                    send_telegram(
                        message
                    )

                    status_state[
                        state_key
                    ] = current_record

                else:

                    print(
                        "No allotment status change."
                    )

            # Be gentle with KFin API
            time.sleep(2)

    save_status_state(
        status_state
    )


# ============================================================
# SELECT IPOs TO CHECK
# ============================================================

def select_ipos_to_check(
    ipo_records,
    newly_detected
):

    if not ipo_records:
        return []

    # Optional manual list.
    #
    # Example:
    #
    # KFIN_IPOS_TO_CHECK=
    # INNOVISION LIMITED-IPO,
    # RAJPUTANA STAINLESS LIMITED-IPO
    #
    manual = os.getenv(
        "KFIN_IPOS_TO_CHECK",
        ""
    ).strip()

    if manual:

        requested = {
            x.strip().upper()
            for x in manual.split(",")
            if x.strip()
        }

        selected = [
            ipo
            for ipo in ipo_records
            if ipo["name"].upper()
            in requested
        ]

        print()
        print(
            "Using manually selected KFin IPOs:",
            len(selected)
        )

        return selected

    # If new IPOs were detected, check those first.
    new_records = [
        ipo
        for ipo in ipo_records
        if ipo["name"] in newly_detected
    ]

    if new_records:

        selected = new_records[
            :MAX_IPOS_TO_CHECK
        ]

        print()
        print(
            "Checking newly detected KFin IPOs:",
            len(selected)
        )

        return selected

    # Otherwise check the most recent IPOs
    # from the embedded KFin list.
    selected = ipo_records[
        :MAX_IPOS_TO_CHECK
    ]

    print()
    print(
        "No new IPOs detected."
    )

    print(
        "Checking recent KFin IPOs:",
        len(selected)
    )

    return selected


# ============================================================
# MAIN MONITOR
# ============================================================

async def monitor_kfin():

    previous_ipos = load_state()

    print(
        "Previously detected KFin IPOs:",
        len(previous_ipos)
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        # Request logging
        def log_request(request):

            print(
                "REQUEST:",
                request.method,
                request.url
            )

        page.on(
            "request",
            log_request
        )

        print()
        print(
            "Opening KFintech..."
        )

        await page.goto(
            KFIN_URL,
            wait_until="domcontentloaded",
            timeout=60000
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

        if not bundle_url:

            print(
                "Could not find KFin JavaScript bundle."
            )

            await browser.close()
            return

        print()
        print(
            "KFin JavaScript bundle:"
        )

        print(bundle_url)

        bundle = download_bundle(
            bundle_url
        )

        if not bundle:

            await browser.close()
            return

        # Debug information
        find_api_urls(bundle)
        find_submit_logic(bundle)

        # Extract IPO records
        ipo_records = extract_ipo_records(
            bundle
        )

        print()
        print(
            "Total KFin IPO records:",
            len(ipo_records)
        )

        if not ipo_records:

            print(
                "No KFin IPO records found."
            )

            await browser.close()
            return

        current_ipos = {
            ipo["name"]
            for ipo in ipo_records
        }

        new_ipos = (
            current_ipos
            - previous_ipos
        )

        print()
        print(
            "New KFin IPOs detected:",
            len(new_ipos)
        )

        for name in sorted(new_ipos):

            print(
                "NEW KFIN IPO:",
                name
            )

        # Telegram alert for new IPOs
        if previous_ipos:

            for name in sorted(new_ipos):

                message = (
                    "New KFintech IPO detected\n\n"
                    f"IPO: {name}"
                )

                send_telegram(
                    message
                )

        else:

            print()
            print(
                "First KFin run detected."
            )

            print(
                "Saving current IPOs as baseline."
            )

        # Save IPO discovery state
        save_state(
            current_ipos
        )

        await browser.close()

    # --------------------------------------------------------
    # ALLOTMENT STATUS
    # --------------------------------------------------------

    pans = get_kfin_pans()

    if not pans:

        print()
        print(
            "Skipping KFin allotment checks."
        )

        return

    selected_ipos = select_ipos_to_check(
        ipo_records,
        new_ipos
    )

    if not selected_ipos:

        print(
            "No IPOs selected for allotment check."
        )

        return

    check_allotment_status(
        selected_ipos,
        pans
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        monitor_kfin()
    )
