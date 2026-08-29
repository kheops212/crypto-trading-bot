# Crypto Trading Bot

A fully automated, multi-asset trading bot supporting **crypto, stocks/ETFs, and forex** — with a live Streamlit dashboard, push notifications, and backtested strategy selection.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/YOUR_USERNAME)

---

## Features

- **42 symbols** — 17 crypto (Kraken), 22 stocks/ETFs (Alpaca), 3 forex
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

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/crypto-trading-bot.git
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

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/YOUR_USERNAME)

## License

MIT — see [LICENSE](LICENSE)
