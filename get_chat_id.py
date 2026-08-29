"""
Run after sending /start to your bot in Telegram.
Prints the correct TELEGRAM_CHAT_ID to paste into your .env file.
"""
import requests
import config

if not config.TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_TOKEN is not set in your .env file.")
else:
    r = requests.get(
        f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/getUpdates",
        timeout=30,
    )
    data = r.json()
    if not data.get("result"):
        print("No messages found. Make sure you sent /start to your bot in Telegram first, then re-run this script.")
    else:
        for update in data["result"]:
            msg = update.get("message", {})
            chat = msg.get("chat", {})
            print(f"Chat ID : {chat.get('id')}")
            print(f"Username: {chat.get('username', '(none)')}")
            print(f"Name    : {chat.get('first_name', '')} {chat.get('last_name', '')}")
            print(f"\nAdd this to your .env:\nTELEGRAM_CHAT_ID={chat.get('id')}")
            break
