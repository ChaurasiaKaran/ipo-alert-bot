import os
import sys
import json
import asyncio
import requests

from playwright.async_api import async_playwright

KFIN_URL = os.getenv("KFIN_URL", "https://ipostatus.kfintech.com/ipostatus")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

STATE_FILE = os.getenv("KFIN_STATE_FILE", "kfin_seen_ipos.json")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Hide the usual "I am a bot" signals
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-IN', 'en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = window.chrome || {runtime: {}};
"""

# Runs inside the page: finds the <select> with the most options
EXTRACT_JS = """
() => {
  let best = null;
  for (const sel of document.querySelectorAll('select')) {
    const n = sel.options.length;
    if (!best || n > best.options.length) best = sel;
  }
  if (!best) return [];
  return Array.from(best.options).map(o => [o.value, o.textContent.trim()]);
}
"""


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


async def dump_debug(page, log):
    print("---- DEBUG ----")
    try:
        print("Page URL:", page.url)
        print("Page title:", await page.title())
        html = await page.content()
        print("HTML length:", len(html))
        root = await page.evaluate(
            "() => { const r = document.getElementById('root');"
            " return r ? r.innerHTML.length : -1; }"
        )
        print("#root content length (-1 = no #root):", root)
        body = (await page.inner_text("body"))[:300]
        print("Body text:", body.replace("\n", " | ") or "(empty)")
        print("Select elements on page:", await page.locator("select").count())
        await page.screenshot(path="/tmp/kfin_debug.png", full_page=True)
    except Exception as e:
        print("Debug capture failed:", type(e).__name__)
    print("Requests/responses seen:", len(log))
    for line in log[:25]:
        print("  ", line)
    print("---------------")


async def get_ipos():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        context = await browser.new_context(
            user_agent=UA,
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1366, "height": 768},
        )
        await context.add_init_script(STEALTH_JS)
        page = await context.new_page()

        log = []
        page.on("requestfailed", lambda r: log.append(
            f"FAILED {r.method} {r.url[:100]} | {r.failure}"))
        page.on("response", lambda r: log.append(
            f"HTTP {r.status} {r.request.resource_type} {r.url[:100]}"))
        page.on("pageerror", lambda e: log.append(f"PAGEERROR {str(e)[:150]}"))
        page.on("console", lambda m: log.append(
            f"CONSOLE {m.type}: {m.text[:120]}") if m.type == "error" else None)

        try:
            for attempt in range(1, 4):
                try:
                    await page.goto(KFIN_URL, wait_until="domcontentloaded", timeout=60000)
                    # wait until some <select> has more than 1 option
                    await page.wait_for_function(
                        "() => Array.from(document.querySelectorAll('select'))"
                        ".some(s => s.options.length > 1)",
                        timeout=40000,
                    )
                    rows = await page.evaluate(EXTRACT_JS)
                    ipos = {}
                    for value, name in rows:
                        value = (value or "").strip()
                        if not value or not name or value in ("0", "-1"):
                            continue
                        ipos[value] = name
                    if ipos:
                        return ipos
                    print(f"Attempt {attempt}: dropdown found but empty")
                except Exception as e:
                    print(f"Attempt {attempt} failed: {type(e).__name__}")
                    log.append(f"--- attempt {attempt} ended ---")
                    await page.wait_for_timeout(3000)

            print("ERROR: KFin IPO dropdown never loaded (blocked or page changed).")
            await dump_debug(page, log)
            return None
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
