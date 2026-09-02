<img width="1214" height="683" alt="Screenshot 2026-08-29 at 00-35-06 Crypto Bot Dashboard" src="https://github.com/user-attachments/assets/ddc6bccf-8a19-43e3-834f-07bf0709a1dd" />
<img width="1214" height="683" alt="Screenshot 2026-08-29 at 00-34-46 Crypto Bot Dashboard" src="https://github.com/user-attachments/assets/fedd7efe-87f8-4f7d-93f6-76eb322386aa" />
<img width="1214" height="683" alt="Screenshot 2026-08-29 at 00-34-11 Crypto Bot Dashboard" src="https://github.com/user-attachments/assets/cd399d47-fc54-4148-bae7-6abe55d3e61a" />
<img width="1214" height="683" alt="Screenshot 2026-08-29 at 00-33-43 Crypto Bot Dashboard" src="https://github.com/user-attachments/assets/1fee0ab1-fd9c-4c6a-afbb-d8bd9f32c383" />
# Crypto Trading Bot

A fully automated, multi-asset trading bot supporting **crypto, stocks/ETFs, and forex** — with a live Streamlit dashboard, push notifications, and backtested strategy selection.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/kheops212)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-2CA5E0?style=for-the-badge&logo=telegram)](https://t.me/CryptoTradingLive26_bot)
[![Telegram Channel](https://img.shields.io/badge/Telegram-Live%20Trades-2CA5E0?style=for-the-badge&logo=telegram)](https://t.me/CryptoTradingLive26)

---

## Community

| | Link |
|---|---|
| 📢 **Live trade channel** | [@CryptoTradingLive26](https://t.me/CryptoTradingLive26) — every real trade posted automatically |
| 🤖 **Telegram bot** | [@CryptoTradingLive26_bot](https://t.me/CryptoTradingLive26_bot) — commands: `/start`, `/features`, `/strategy`, `/results`, `/github`, `/coffee` |

## Features

- **49 symbols** — 19 crypto (Kraken), 27 stocks/ETFs (Alpaca), 3 forex
- **5 strategies** — EMA crossover, RSI reversal, MACD, Bollinger Bands, Combined
- **RSI reversal** with 200 EMA trend filter (default, backtested for best win rate)
- **Trailing stop-loss** — stop moves up as price rises, locking in profit
- **5-minute SL/TP checks** + hourly strategy signals
- **Streamlit dashboard** — strategy comparison, RSI optimizer, P&L summary, positions, notifications
- **Push notifications** via [ntfy.sh](https://ntfy.sh) — trades fire to your phone instantly
- **systemd services** — runs 24/7, survives logout, auto-restarts on crash
- **Paper trading mode** — test safely with simulated fills via Yahoo Finance

## Supported Exchanges

| Asset Class | Live Broker | Paper Trading |
|---|---|---|
| Crypto | [Kraken](https://kraken.com) | Yahoo Finance (simulated) |
| Stocks / ETFs | [Alpaca](https://alpaca.markets) | Alpaca paper account |
| Forex | OANDA (coming soon) | Yahoo Finance (simulated) |

## Dashboard

- **Strategy Performance** — backtest all 5 strategies on any symbol, equity curves, risk/reward scatter
- **Optimize RSI** — grid search over RSI period, oversold, overbought — find best params per asset
- **P&L Summary** — cumulative P&L chart, by asset class, by symbol, exit reason breakdown, withdrawal tracker
- **Positions** — live positions with trailing stop levels, unrealized P&L
- **Notifications** — color-coded trade feed with new badge count
- **Trade History** — full log of all trades

## Quickstart

### Linux / macOS

```bash
# 1. Clone
git clone https://github.com/kheops212/crypto-trading-bot.git
cd crypto-trading-bot

# 2. Create virtual environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your API keys

# 4. Run (paper trading by default)
./run_bot.sh        # terminal 1
./run_dashboard.sh  # terminal 2
```

### Windows

```powershell
# 1. Clone
git clone https://github.com/kheops212/crypto-trading-bot.git
cd crypto-trading-bot

# 2. Run setup (creates venv, installs dependencies, copies .env)
setup.bat

# 3. Edit .env with your API keys

# 4. Run
run_bot.bat        # terminal 1
run_dashboard.bat  # terminal 2
```

**Run as a Windows service (survives logout, auto-starts on reboot):**
1. Download [nssm.exe](https://nssm.cc/download) and place it in the project folder
2. Open PowerShell as Administrator
3. Run: `.\install_service_windows.ps1`

```powershell
# Manage the service
nssm stop crypto-bot
nssm start crypto-bot
nssm restart crypto-bot
```

## Configuration

All settings are in `config.py`:

```python
SYMBOLS       = ["BTC/USDT", "ETH/USDT", ...]   # crypto pairs
STOCK_SYMBOLS = ["NVDA", "SPY", ...]              # stocks & ETFs
FOREX_SYMBOLS = ["EUR/USD", "GBP/USD", ...]       # forex pairs

STRATEGY      = "rsi_reversal"   # active strategy
TRAILING_STOP = True             # trailing stop-loss
TRADE_AMOUNT_USDT = 10.0         # $ per trade
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```
EXCHANGE=kraken
API_KEY=your_kraken_key
API_SECRET=your_kraken_secret
PAPER_TRADE=true                 # set false for live crypto

ALPACA_KEY=your_alpaca_key
ALPACA_SECRET=your_alpaca_secret
ALPACA_PAPER=true                # set false for live stocks

NTFY_TOPIC=your-unique-topic     # push notifications (optional)

TELEGRAM_MARKETING_TOKEN=your_bot_token   # Telegram marketing bot (optional)
TELEGRAM_CHANNEL_ID=@YourChannel          # Telegram live trade channel (optional)
```

## Running as a Service (Linux)

```bash
# Create symlink (avoids spaces/special chars in path)
ln -s "$(pwd)" ~/cryptobot

# Install systemd services
bash install_services.sh

# Check status
sudo systemctl status crypto-bot
sudo systemctl status crypto-dashboard

# View live logs
journalctl -u crypto-bot -f
```

## Backtesting

```bash
# Backtest a specific strategy
.venv/bin/python backtest.py rsi_reversal

# Or use the Optimize RSI tab in the dashboard for a full grid search
```

## Disclaimer

This software is for educational purposes only. Trading involves significant risk of loss. Past backtest performance does not guarantee future results. Always start with paper trading and only risk capital you can afford to lose.

## Support

If this project helped you, consider buying me a coffee!

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/kheops212)

## License

MIT — see [LICENSE](LICENSE)
