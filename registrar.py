import os
import requests
from telegram import Bot

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

URL = "https://in.mpms.mufg.com/Initial_Offer/public-issues.html"

bot = Bot(token=TOKEN)


def check_registrar():
    response = requests.get(
        URL,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    page = response.text.lower()

    if "manika" in page:
        return True

    return False


def send_alert():
    import asyncio

    asyncio.run(
        bot.send_message(
            chat_id=CHAT_ID,
            text=(
                "🚨 IPO ALLOTMENT PORTAL UPDATE\n\n"
                "IPO: Manika Plastech\n"
                "Registrar: MUFG Intime\n\n"
                "Manika Plastech was detected on the "
                "official registrar page.\n\n"
                f"🔗 {URL}"
            )
        )
    )


if __name__ == "__main__":
    found = check_registrar()

    if found:
        send_alert()
        print("Manika Plastech detected!")
    else:
        print("IPO not detected yet.")
