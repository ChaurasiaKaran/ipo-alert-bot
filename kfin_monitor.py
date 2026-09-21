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

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    ""
).strip()


# ============================================================
# MULTIPLE PAN SUPPORT
# ============================================================

# Example:
#
# KFIN_PANS=ABCDE1234F,XYZAB5678C,PQRST9012D
#
# Existing KFIN_PAN is supported as fallback.

KFIN_PANS = os.getenv(
    "KFIN_PANS",
    ""
).strip()

OLD_KFIN_PAN = os.getenv(
    "KFIN_PAN",
    ""
).strip()


# ============================================================
# STATE FILES
# ============================================================

# Previously detected IPO names
STATE_FILE = "kfin_state.txt"

# Allotment status history
STATUS_STATE_FILE = "kfin_status_state.json"

# Telegram-selected IPOs
TRACKING_FILE = "kfin_tracking.json"

# Telegram getUpdates offset
TELEGRAM_STATE_FILE = "telegram_state.json"


# ============================================================
# TELEGRAM HELPERS
# ============================================================

def telegram_api(method, payload=None):

    if not TELEGRAM_BOT_TOKEN:
        print("Telegram bot token is not configured.")
        return None

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/{method}"
    )

    try:

        response = requests.post(
            url,
            json=payload or {},
            timeout=30,
        )

        if response.status_code != 200:

            print(
                "Telegram API error:",
                response.status_code
            )

            return None

        data = response.json()

        if not data.get("ok"):

            print(
                "Telegram API returned an error."
            )

            return None

        return data

    except requests.RequestException as e:

        print(
            "Telegram request failed:",
            type(e).__name__
        )

        return None

    except ValueError:

        print(
            "Telegram returned invalid JSON."
        )

        return None


def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:

        print(
            "Telegram credentials are not configured."
        )

        return False

    result = telegram_api(
        "sendMessage",
        {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
        }
    )

    if result:

        print(
            "Telegram message sent."
        )

        return True

    return False


def answer_callback(callback_query_id):

    if not callback_query_id:
        return

    telegram_api(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_query_id
        }
    )


def edit_telegram_message(
    chat_id,
    message_id,
    text,
    reply_markup=None
):

    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }

    if reply_markup is not None:

        payload["reply_markup"] = reply_markup

    return telegram_api(
        "editMessageText",
        payload
    )


# ============================================================
# TELEGRAM STATE
# ============================================================

def load_telegram_offset():

    if not os.path.exists(
        TELEGRAM_STATE_FILE
    ):

        return 0

    try:

        with open(
            TELEGRAM_STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        return int(
            data.get(
                "last_update_id",
                0
            )
        )

    except Exception as e:

        print(
            "Could not read Telegram state:",
            type(e).__name__
        )

        return 0


def save_telegram_offset(update_id):

    try:

        with open(
            TELEGRAM_STATE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                {
                    "last_update_id": update_id
                },
                f,
                indent=2
            )

    except Exception as e:

        print(
            "Could not save Telegram state:",
            type(e).__name__
        )


# ============================================================
# IPO TRACKING STATE
# ============================================================

def load_tracking():

    if not os.path.exists(
        TRACKING_FILE
    ):

        return {
            "selected_ipos": []
        }

    try:

        with open(
            TRACKING_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if not isinstance(data, dict):

            return {
                "selected_ipos": []
            }

        selected = data.get(
            "selected_ipos",
            []
        )

        if not isinstance(
            selected,
            list
        ):

            selected = []

        return {
            "selected_ipos": selected
        }

    except Exception as e:

        print(
            "Could not read KFin tracking state:",
            type(e).__name__
        )

        return {
            "selected_ipos": []
        }


def save_tracking(tracking):

    try:

        with open(
            TRACKING_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                tracking,
                f,
                indent=2,
                ensure_ascii=False
            )

        print(
            "KFin IPO tracking state saved."
        )

    except Exception as e:

        print(
            "Could not save tracking state:",
            type(e).__name__
        )


def get_tracked_client_ids(tracking):

    ids = set()

    for ipo in tracking.get(
        "selected_ipos",
        []
    ):

        if not isinstance(
            ipo,
            dict
        ):

            continue

        client_id = str(
            ipo.get(
                "client_id",
                ""
            )
        ).strip()

        if client_id:

            ids.add(client_id)

    return ids


# ============================================================
# TELEGRAM MENU
# ============================================================

ITEMS_PER_PAGE = 8


def shorten_ipo_name(
    name,
    maximum=38
):

    if len(name) <= maximum:

        return name

    return name[:maximum - 3] + "..."


def build_menu(
    ipo_records,
    tracking,
    page=0
):

    if not ipo_records:

        return (
            "📊 KFin IPO Tracker\n\n"
            "No IPOs were found."
        ), {
            "inline_keyboard": []
        }

    total_pages = (
        len(ipo_records)
        + ITEMS_PER_PAGE
        - 1
    ) // ITEMS_PER_PAGE

    if page < 0:
        page = 0

    if page >= total_pages:
        page = total_pages - 1

    start = (
        page
        * ITEMS_PER_PAGE
    )

    end = start + ITEMS_PER_PAGE

    page_records = ipo_records[
        start:end
    ]

    tracked_ids = get_tracked_client_ids(
        tracking
    )

    lines = [
        "📊 KFin IPO Tracker",
        "",
        "🟢 = Tracking",
        "⚪ = Not tracking",
        "",
        f"Page {page + 1}/{total_pages}",
        ""
    ]

    keyboard = []

    for ipo in page_records:

        client_id = ipo[
            "client_id"
        ]

        name = ipo[
            "name"
        ]

        if client_id in tracked_ids:

            icon = "🟢"

        else:

            icon = "⚪"

        lines.append(
            f"{icon} {name}"
        )

        if client_id in tracked_ids:

            button_text = (
                "🟢 "
                + shorten_ipo_name(name)
            )

        else:

            button_text = (
                "⚪ "
                + shorten_ipo_name(name)
            )

        keyboard.append([
            {
                "text": button_text,
                "callback_data": (
                    "toggle|"
                    + client_id
                    + "|"
                    + str(page)
                )
            }
        ])

    navigation = []

    if page > 0:

        navigation.append({
            "text": "⬅️",
            "callback_data": (
                "page|"
                + str(page - 1)
            )
        })

    navigation.append({
        "text": (
            f"{page + 1}/{total_pages}"
        ),
        "callback_data": (
            "noop"
        )
    })

    if page < total_pages - 1:

        navigation.append({
            "text": "➡️",
            "callback_data": (
                "page|"
                + str(page + 1)
            )
        })

    keyboard.append(
        navigation
    )

    keyboard.append([
        {
            "text": "📋 Tracked IPOs",
            "callback_data": "tracked"
        }
    ])

    keyboard.append([
        {
            "text": "❌ Untrack All",
            "callback_data": "untrackall"
        }
    ])

    return (
        "\n".join(lines),
        {
            "inline_keyboard": keyboard
        }
    )


def send_ipo_menu(
    ipo_records,
    tracking,
    page=0
):

    text, keyboard = build_menu(
        ipo_records,
        tracking,
        page
    )

    return telegram_api(
        "sendMessage",
        {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "reply_markup": keyboard,
        }
    )


def tracked_message(tracking):

    selected = tracking.get(
        "selected_ipos",
        []
    )

    if not selected:

        return (
            "📋 KFin IPO Tracker\n\n"
            "No IPOs are currently being tracked.\n\n"
            "Use /menu to select IPOs."
        )

    lines = [
        "📋 Currently Tracked IPOs",
        ""
    ]

    for index, ipo in enumerate(
        selected,
        start=1
    ):

        name = ipo.get(
            "name",
            "Unknown IPO"
        )

        lines.append(
            f"{index}. {name}"
        )

    lines.extend([
        "",
        "Use /menu to change your selection."
    ])

    return "\n".join(lines)


# ============================================================
# TELEGRAM IPO TOGGLE
# ============================================================

def toggle_ipo(
    tracking,
    ipo_records,
    client_id
):

    selected = tracking.setdefault(
        "selected_ipos",
        []
    )

    existing_index = None

    for index, ipo in enumerate(
        selected
    ):

        if str(
            ipo.get(
                "client_id",
                ""
            )
        ) == str(client_id):

            existing_index = index
            break

    # Untrack
    if existing_index is not None:

        removed = selected.pop(
            existing_index
        )

        save_tracking(
            tracking
        )

        print(
            "Untracked IPO:",
            removed.get("name", "")
        )

        return False

    # Track
    for ipo in ipo_records:

        if str(
            ipo["client_id"]
        ) == str(client_id):

            selected.append({
                "client_id": ipo[
                    "client_id"
                ],
                "name": ipo[
                    "name"
                ]
            })

            save_tracking(
                tracking
            )

            print(
                "Tracked IPO:",
                ipo["name"]
            )

            return True

    print(
        "Could not find IPO:",
        client_id
    )

    return None


# ============================================================
# TELEGRAM UPDATE PROCESSING
# ============================================================

def get_telegram_updates():

    if not TELEGRAM_BOT_TOKEN:
        return []

    offset = load_telegram_offset()

    payload = {
        "timeout": 1,
        "allowed_updates": [
            "message",
            "callback_query"
        ]
    }

    if offset > 0:

        payload["offset"] = (
            offset + 1
        )

    result = telegram_api(
        "getUpdates",
        payload
    )

    if not result:

        return []

    return result.get(
        "result",
        []
    )


def process_telegram_updates(
    ipo_records
):

    if not TELEGRAM_BOT_TOKEN:

        print(
            "Telegram bot token not configured."
        )

        return

    if not TELEGRAM_CHAT_ID:

        print(
            "Telegram chat ID not configured."
        )

        return

    updates = get_telegram_updates()

    if not updates:

        print(
            "No new Telegram commands."
        )

        return

    tracking = load_tracking()

    for update in updates:

        update_id = update.get(
            "update_id"
        )

        try:

            # ==================================================
            # CALLBACK BUTTON
            # ==================================================

            callback = update.get(
                "callback_query"
            )

            if callback:

                callback_id = callback.get(
                    "id"
                )

                callback_data = callback.get(
                    "data",
                    ""
                )

                callback_message = (
                    callback.get(
                        "message"
                    )
                    or {}
                )

                callback_chat = (
                    callback_message.get(
                        "chat"
                    )
                    or {}
                )

                callback_chat_id = str(
                    callback_chat.get(
                        "id",
                        ""
                    )
                )

                message_id = callback_message.get(
                    "message_id"
                )

                # Security: only your configured chat
                if (
                    callback_chat_id
                    != str(TELEGRAM_CHAT_ID)
                ):

                    answer_callback(
                        callback_id
                    )

                    if update_id is not None:

                        save_telegram_offset(
                            update_id
                        )

                    continue

                answer_callback(
                    callback_id
                )

                # ----------------------------------------------
                # NO-OP
                # ----------------------------------------------

                if callback_data == "noop":

                    pass

                # ----------------------------------------------
                # TOGGLE IPO
                # ----------------------------------------------

                elif callback_data.startswith(
                    "toggle|"
                ):

                    parts = callback_data.split(
                        "|"
                    )

                    if len(parts) >= 3:

                        client_id = parts[1]

                        try:

                            page = int(
                                parts[2]
                            )

                        except ValueError:

                            page = 0

                        toggle_ipo(
                            tracking,
                            ipo_records,
                            client_id
                        )

                        text, keyboard = build_menu(
                            ipo_records,
                            tracking,
                            page
                        )

                        if message_id:

                            edit_telegram_message(
                                callback_chat_id,
                                message_id,
                                text,
                                keyboard
                            )

                # ----------------------------------------------
                # PAGE
                # ----------------------------------------------

                elif callback_data.startswith(
                    "page|"
                ):

                    parts = callback_data.split(
                        "|"
                    )

                    try:

                        page = int(
                            parts[1]
                        )

                    except (
                        ValueError,
                        IndexError
                    ):

                        page = 0

                    text, keyboard = build_menu(
                        ipo_records,
                        tracking,
                        page
                    )

                    if message_id:

                        edit_telegram_message(
                            callback_chat_id,
                            message_id,
                            text,
                            keyboard
                        )

                # ----------------------------------------------
                # TRACKED
                # ----------------------------------------------

                elif callback_data == "tracked":

                    text = tracked_message(
                        tracking
                    )

                    keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "📊 Back to IPO Menu",
                                    "callback_data": "page|0"
                                }
                            ]
                        ]
                    }

                    if message_id:

                        edit_telegram_message(
                            callback_chat_id,
                            message_id,
                            text,
                            keyboard
                        )

                # ----------------------------------------------
                # UNTRACK ALL
                # ----------------------------------------------

                elif callback_data == "untrackall":

                    tracking[
                        "selected_ipos"
                    ] = []

                    save_tracking(
                        tracking
                    )

                    text = (
                        "❌ All IPO tracking "
                        "selections have been removed.\n\n"
                        "Use /menu to select IPOs again."
                    )

                    keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "📊 Open IPO Menu",
                                    "callback_data": "page|0"
                                }
                            ]
                        ]
                    }

                    if message_id:

                        edit_telegram_message(
                            callback_chat_id,
                            message_id,
                            text,
                            keyboard
                        )

            # ==================================================
            # NORMAL MESSAGE
            # ==================================================

            message = update.get(
                "message"
            )

            if message:

                chat = message.get(
                    "chat"
                ) or {}

                chat_id = str(
                    chat.get(
                        "id",
                        ""
                    )
                )

                # Security: only your configured chat
                if chat_id != str(
                    TELEGRAM_CHAT_ID
                ):

                    if update_id is not None:

                        save_telegram_offset(
                            update_id
                        )

                    continue

                text = (
                    message.get(
                        "text",
                        ""
                    )
                    .strip()
                )

                command = (
                    text.split()[0].lower()
                    if text
                    else ""
                )

                # ----------------------------------------------
                # /menu
                # ----------------------------------------------

                if command == "/menu":

                    send_ipo_menu(
                        ipo_records,
                        tracking,
                        0
                    )

                # ----------------------------------------------
                # /tracked
                # ----------------------------------------------

                elif command == "/tracked":

                    send_telegram(
                        tracked_message(
                            tracking
                        )
                    )

                # ----------------------------------------------
                # /untrackall
                # ----------------------------------------------

                elif command == "/untrackall":

                    tracking[
                        "selected_ipos"
                    ] = []

                    save_tracking(
                        tracking
                    )

                    send_telegram(
                        "❌ All KFin IPO tracking "
                        "selections have been removed."
                    )

                # ----------------------------------------------
                # /start
                # ----------------------------------------------

                elif command == "/start":

                    send_telegram(
                        "📊 KFin IPO Tracker\n\n"
                        "Use /menu to select the IPOs "
                        "you want to track.\n\n"
                        "Commands:\n"
                        "/menu - Select IPOs\n"
                        "/tracked - Show tracked IPOs\n"
                        "/untrackall - Remove all selections"
                    )

                # ----------------------------------------------
                # UNKNOWN COMMAND
                # ----------------------------------------------

                elif command.startswith("/"):

                    send_telegram(
                        "Unknown command.\n\n"
                        "Use /menu to select IPOs."
                    )

            if update_id is not None:

                save_telegram_offset(
                    update_id
                )

        except Exception as e:

            print(
                "Error processing Telegram update:",
                type(e).__name__
            )

            # Still advance update offset so a malformed
            # update doesn't get processed forever.
            if update_id is not None:

                save_telegram_offset(
                    update_id
                )


# ============================================================
# IPO DISCOVERY STATE
# ============================================================

def load_state():

    if not os.path.exists(
        STATE_FILE
    ):

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

            for name in sorted(
                ipo_names
            ):

                f.write(
                    name + "\n"
                )

        print(
            "KFin IPO state saved successfully."
        )

    except Exception as e:

        print(
            "Could not save KFin state:",
            type(e).__name__
        )


# ============================================================
# ALLOTMENT STATUS STATE
# ============================================================

def load_status_state():

    if not os.path.exists(
        STATUS_STATE_FILE
    ):

        return {}

    try:

        with open(
            STATUS_STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(
            data,
            dict
        ):

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

        print(
            "KFin allotment state saved successfully."
        )

    except Exception as e:

        print(
            "Could not save KFin status state:",
            type(e).__name__
        )


# ============================================================
# PAN HANDLING
# ============================================================

def get_kfin_pans():

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

                pans.append(
                    pan
                )

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

    if len(pan) != 10:

        return "XXXXX"

    return (
        "XXXXX"
        + pan[5:]
    )


# ============================================================
# KFIN JAVASCRIPT BUNDLE
# ============================================================

async def get_bundle_url(page):

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
    print(
        "Downloading KFin bundle..."
    )

    try:

        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=30,
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

        seen_ids.add(
            client_id
        )

        records.append({
            "client_id": client_id,
            "name": name,
        })

    return records


# ============================================================
# KFIN API
# ============================================================

def query_kfin_pan(
    ipo_client_id,
    pan
):

    """
    Query KFin using PAN.

    The PAN itself is never printed.
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

        if isinstance(
            data,
            dict
        ):

            outer = data.get(
                "data"
            )

            if isinstance(
                outer,
                dict
            ):

                rows = outer.get(
                    "data",
                    []
                )

            elif isinstance(
                outer,
                list
            ):

                rows = outer

        if not isinstance(
            rows,
            list
        ):

            rows = []

        results = []

        for row in rows:

            if not isinstance(
                row,
                dict
            ):

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
    tracked_ipos,
    pans
):

    if not pans:

        print(
            "No PANs available."
        )

        return

    if not tracked_ipos:

        print()
        print(
            "No IPOs selected for tracking."
        )

        return

    print()
    print("=" * 80)
    print(
        "KFIN SELECTED IPO ALLOTMENT CHECK"
    )
    print("=" * 80)

    print(
        "PANs to check:",
        len(pans)
    )

    print(
        "Selected IPOs:",
        len(tracked_ipos)
    )

    status_state = load_status_state()

    for ipo in tracked_ipos:

        ipo_name = ipo[
            "name"
        ]

        client_id = ipo[
            "client_id"
        ]

        print()
        print(
            "Checking IPO:",
            ipo_name
        )

        for pan in pans:

            masked_pan = mask_pan(
                pan
            )

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
                    "Stopping this run."
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
                    row.get(
                        "ipo_title"
                    )
                    or ipo_name
                )

                print(
                    f"Result: {status} | "
                    f"Shares: {shares} | "
                    f"Applied: {applied}"
                )

                # We don't store the actual PAN.
                state_key = (
                    f"{masked_pan}|"
                    f"{client_id}"
                )

                current_record = {
                    "status": status,
                    "shares": shares,
                    "applied": applied,
                    "ipo": title,
                }

                previous = status_state.get(
                    state_key
                )

                should_alert = (
                    previous
                    != current_record
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

            # Delay between KFin requests
            time.sleep(2)

    save_status_state(
        status_state
    )


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

        # ----------------------------------------------------
        # REQUEST LOGGING
        # ----------------------------------------------------

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

        try:

            await page.goto(
                KFIN_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

        except Exception as e:

            print(
                "Could not open KFintech:",
                type(e).__name__
            )

            await browser.close()
            return

        await page.wait_for_timeout(
            3000
        )

        print()
        print(
            "Page title:",
            await page.title()
        )

        # ----------------------------------------------------
        # FIND JAVASCRIPT BUNDLE
        # ----------------------------------------------------

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

        print(
            bundle_url
        )

        bundle = download_bundle(
            bundle_url
        )

        if not bundle:

            await browser.close()
            return

        # ----------------------------------------------------
        # EXTRACT IPO LIST
        # ----------------------------------------------------

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

        for name in sorted(
            new_ipos
        ):

            print(
                "NEW IPO:",
                name
            )

        # ----------------------------------------------------
        # SAVE IPO DISCOVERY STATE
        # ----------------------------------------------------

        save_state(
            current_ipos
        )

        # ----------------------------------------------------
        # PROCESS TELEGRAM COMMANDS/BUTTONS
        # ----------------------------------------------------

        print()
        print(
            "Checking Telegram commands..."
        )

        process_telegram_updates(
            ipo_records
        )

        # ----------------------------------------------------
        # LOAD CURRENT TRACKING SELECTION
        # ----------------------------------------------------

        tracking = load_tracking()

        tracked_ids = get_tracked_client_ids(
            tracking
        )

        # ----------------------------------------------------
        # REFRESH TRACKED IPO NAMES FROM CURRENT KFIN LIST
        # ----------------------------------------------------

        current_by_id = {
            ipo["client_id"]: ipo
            for ipo in ipo_records
        }

        refreshed_selected = []

        for selected in tracking.get(
            "selected_ipos",
            []
        ):

            client_id = str(
                selected.get(
                    "client_id",
                    ""
                )
            )

            if client_id in current_by_id:

                current = current_by_id[
                    client_id
                ]

                refreshed_selected.append({
                    "client_id": current[
                        "client_id"
                    ],
                    "name": current[
                        "name"
                    ]
                })

            else:

                # Keep old selection in the file.
                # It may temporarily disappear from KFin's
                # current JavaScript list.
                refreshed_selected.append(
                    selected
                )

        tracking[
            "selected_ipos"
        ] = refreshed_selected

        save_tracking(
            tracking
        )

        # ----------------------------------------------------
        # CHECK SELECTED IPOs
        # ----------------------------------------------------

        tracked_ipos = []

        for selected in tracking.get(
            "selected_ipos",
            []
        ):

            if not isinstance(
                selected,
                dict
            ):

                continue

            if (
                selected.get(
                    "client_id"
                )
                and selected.get(
                    "name"
                )
            ):

                tracked_ipos.append({
                    "client_id": str(
                        selected[
                            "client_id"
                        ]
                    ),
                    "name": str(
                        selected[
                            "name"
                        ]
                    )
                })

        print()
        print(
            "Currently tracked IPOs:",
            len(tracked_ipos)
        )

        for ipo in tracked_ipos:

            print(
                "TRACKED:",
                ipo["name"]
            )

        # ----------------------------------------------------
        # GET PANs
        # ----------------------------------------------------

        pans = get_kfin_pans()

        # ----------------------------------------------------
        # CHECK ALLOTMENT
        # ----------------------------------------------------

        check_allotment_status(
            tracked_ipos,
            pans
        )

        await browser.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        monitor_kfin()
    )
