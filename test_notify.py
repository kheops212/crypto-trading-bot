"""
Test ntfy.sh notifications before running the bot.
Usage: .venv/bin/python test_notify.py
"""
import config
import notifier

if not config.NTFY_TOPIC or config.NTFY_TOPIC == "your-unique-topic-here":
    print("ERROR: NTFY_TOPIC is still the placeholder. Edit your .env file and set a real topic name.")
else:
    print(f"Sending test notification to topic: {config.NTFY_TOPIC}")
    ok = notifier.send(
        title="Crypto Bot connected",
        body="ntfy notifications are working. Your bot is ready.",
        level="success",
    )
    print("Notification sent — check your phone." if ok else "Failed — check your topic name and internet connection.")
