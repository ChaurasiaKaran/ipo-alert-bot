import os
import sys
import json
import asyncio
import requests

from playwright.async_api import async_playwright

KFIN_URL = "https://ipostatus.kfintech.com/ipostatus"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

STATE_FILE = "kfin_seen_ipos.json"


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token/chat ID missing.")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=30,
        )
        r.raise_for_status()
        print("Telegram notification sent.")
        return True
    except Exception as e:
        print("Telegram error:", type(e).__name__)
        return False


def load_state():
    """Returns (seen_set, file_existed)."""
    if not os.path.exists(STATE_FILE):
        return set(), False
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(str(x) for x in data), True
    except Exception:
        return set(), False


def save_state(seen):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, indent=2)


async def get_ipos():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            for attempt in range(1, 4):
                try:
                    await page.goto(KFIN_URL, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_selector(
                        "#ddlCompany option", state="attached", timeout=30000
                    )
                    break
                except Exception as e:
                    print(f"Attempt {attempt} failed: {type(e).__name__}")
                    await page.wait_for_timeout(3000)
            else:
                print("ERROR: KFin IPO dropdown never loaded (blocked or page changed).")
                return None

            options = page.locator("#ddlCompany option")
            count = await options.count()

            ipos = {}
            for i in range(count):
                opt = options.nth(i)
                cid = (await opt.get_attribute("value") or "").strip()
                name = (await opt.inner_text()).strip()
                if not cid or not name or cid in ("0", "-1"):
                    continue
                ipos[cid] = name
            return ipos
        finally:
            await browser.close()


async def main():
    ipos = await get_ipos()

    if ipos is None:
        return 1

    print("IPOs on KFin page:", len(ipos))

    seen, existed = load_state()

    # First run: just remember current IPOs, don't spam old ones
    if not existed:
        save_state(set(ipos.keys()))
        print("First run: saved existing IPOs, no alerts sent.")
        return 0

    new_ids = [cid for cid in ipos if cid not in seen]

    if not new_ids:
        print("No new IPO results.")
        return 0

    for cid in new_ids:
        message = (
            "📢 IPO RESULT IS OUT (KFintech)\n\n"
            f"IPO: {ipos[cid]}\n\n"
            f"Check status:\n{KFIN_URL}"
        )
        if send_telegram(message):
            seen.add(cid)
            save_state(seen)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
