"""
Telegram marketing bot — Option C:
  • Public channel: auto-posts every live trade (social proof)
  • Command bot: responds to /start, /features, /github, /coffee, /strategy, /results

Run: .venv/bin/python telegram_marketing_bot.py
Or via systemd: sudo systemctl start crypto-telegram-bot
"""
import time
import requests
from loguru import logger
import config
import trades

_BASE = "https://api.telegram.org/bot{token}/{method}"

GITHUB_URL  = "https://github.com/kheops212/crypto-trading-bot"
COFFEE_URL  = "https://buymeacoffee.com/kheops212"

# ---------------------------------------------------------------------------
# Telegram API helpers
# ---------------------------------------------------------------------------

def _call(method: str, token: str, payload: dict) -> dict | None:
    try:
        r = requests.post(
            _BASE.format(token=token, method=method),
            json=payload,
            timeout=30,
        )
        if r.ok:
            return r.json()
        logger.warning(f"Telegram {method} error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        logger.warning(f"Telegram {method} failed: {e}")
    return None


def _send(chat_id: str, text: str, parse_mode: str = "Markdown") -> bool:
    result = _call("sendMessage", config.TELEGRAM_MARKETING_TOKEN, {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    })
    return result is not None


# ---------------------------------------------------------------------------
# Channel posting — called from notifier.py when a trade fires
# ---------------------------------------------------------------------------

def post_to_channel(title: str, body: str, level: str = "info") -> bool:
    if not config.TELEGRAM_MARKETING_TOKEN or not config.TELEGRAM_CHANNEL_ID:
        return False
    icons = {"success": "🟢", "error": "🔴", "warning": "🟡", "info": "🔵"}
    icon = icons.get(level, "🔵")
    text = (
        f"{icon} *{title}*\n"
        f"{body}\n\n"
        f"🤖 [Live bot]({GITHUB_URL}) • [Support]({COFFEE_URL})"
    )
    return _send(config.TELEGRAM_CHANNEL_ID, text)


# ---------------------------------------------------------------------------
# Command responses
# ---------------------------------------------------------------------------

COMMANDS = {
    "/start": (
        "👋 *Welcome to the Crypto Trading Bot!*\n\n"
        "I'm a fully automated trading bot that runs across *crypto, stocks/ETFs, and forex* simultaneously.\n\n"
        "Use the commands below to learn more:\n"
        "/features — what I can do\n"
        "/strategy — how I trade\n"
        "/results — recent trades\n"
        "/github — source code\n"
        "/coffee — support the project\n"
        "/help — show all commands"
    ),
    "/help": (
        "📋 *Available Commands*\n\n"
        "/start — welcome message\n"
        "/features — full feature list\n"
        "/strategy — trading strategy explained\n"
        "/results — recent live trades\n"
        "/github — open source repo\n"
        "/coffee — buy me a coffee ☕\n"
    ),
    "/features": (
        "⚙️ *Features*\n\n"
        "• *42 symbols* — crypto (Kraken), stocks/ETFs (Alpaca), forex\n"
        "• *5 strategies* — EMA, RSI, MACD, Bollinger Bands, Combined\n"
        "• *RSI reversal + 200 EMA trend filter* — 75–100% backtested win rates\n"
        "• *Trailing stop-loss* — stop moves up as price rises\n"
        "• *5-min SL/TP checks* + hourly strategy signals\n"
        "• *Streamlit dashboard* — P&L, positions, strategy optimizer\n"
        "• *Push notifications* via ntfy.sh\n"
        "• *24/7 operation* via systemd — survives reboots\n"
        "• *Paper trading mode* — test safely before going live\n\n"
        f"🔗 [View on GitHub]({GITHUB_URL})"
    ),
    "/strategy": (
        "📊 *Trading Strategy*\n\n"
        "*RSI Reversal + 200 EMA Trend Filter*\n\n"
        "• Only buys when RSI crosses up through oversold (25) — genuine dip recoveries\n"
        "• Sells when RSI reaches overbought (55)\n"
        "• 200 EMA trend filter blocks buys in downtrends — avoids falling knives\n"
        "• Trailing stop-loss locks in profit as price rises\n\n"
        "*Backtested win rates (1 year, hourly data):*\n"
        "BTC/USDT — 57.9% | AVAX — 83.3% | GS — 100% | SOXX — 83.3%\n\n"
        f"🔗 [Full backtest details]({GITHUB_URL})"
    ),
    "/github": (
        f"👨‍💻 *Open Source*\n\n"
        f"The full source code is free on GitHub:\n{GITHUB_URL}\n\n"
        "⭐ Star the repo if it helped you!"
    ),
    "/coffee": (
        f"☕ *Support the Project*\n\n"
        f"If this bot helped you, consider buying me a coffee!\n{COFFEE_URL}\n\n"
        "Every contribution helps keep the project maintained and updated. 🙏"
    ),
}


def _results_message() -> str:
    closed = trades.get_closed_positions(limit=5)
    if not closed:
        return "📭 *Recent Trades*\n\nNo closed trades yet — the bot is running and waiting for signals."

    lines = ["📈 *Recent Trades*\n"]
    for p in closed:
        pnl = (p["close_price"] - p["entry_price"]) * p["amount"]
        pnl_pct = (p["close_price"] / p["entry_price"] - 1) * 100
        icon = "🟢" if pnl >= 0 else "🔴"
        date = p["closed_at"][:10] if p["closed_at"] else "—"
        lines.append(
            f"{icon} *{p['symbol']}* — {p['close_reason']}\n"
            f"   Entry: ${p['entry_price']:,.4f} → Close: ${p['close_price']:,.4f}\n"
            f"   P&L: {pnl:+.4f} ({pnl_pct:+.2f}%) | {date}"
        )
    lines.append(f"\n🔗 [Live dashboard & more]({GITHUB_URL})")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------

def _get_updates(offset: int) -> list[dict]:
    result = _call("getUpdates", config.TELEGRAM_MARKETING_TOKEN, {
        "offset": offset,
        "timeout": 20,
        "allowed_updates": ["message"],
    })
    if result and result.get("ok"):
        return result.get("result", [])
    return []


def _handle_update(update: dict):
    msg = update.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "").strip().lower().split("@")[0]  # strip bot username

    if not chat_id or not text.startswith("/"):
        return

    if text in COMMANDS:
        _send(chat_id, COMMANDS[text])
    elif text == "/results":
        _send(chat_id, _results_message())
    else:
        _send(chat_id, "❓ Unknown command. Use /help to see available commands.")


def run():
    if not config.TELEGRAM_MARKETING_TOKEN:
        logger.error("TELEGRAM_MARKETING_TOKEN not set — bot cannot start.")
        return

    logger.info("Telegram marketing bot started (polling)...")
    offset = 0
    while True:
        try:
            updates = _get_updates(offset)
            for update in updates:
                _handle_update(update)
                offset = update["update_id"] + 1
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run()
