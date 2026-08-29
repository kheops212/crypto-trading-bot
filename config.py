import os
from dotenv import load_dotenv

load_dotenv()

EXCHANGE = os.getenv("EXCHANGE", "binance")
API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")
PAPER_TRADE = os.getenv("PAPER_TRADE", "true").lower() == "false"

# ntfy.sh push notifications (optional — leave blank to disable)
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")

# Alpaca — live stock trading (leave blank to use paper/simulated)
ALPACA_KEY    = os.getenv("ALPACA_KEY", "")
ALPACA_SECRET = os.getenv("ALPACA_SECRET", "")
ALPACA_PAPER  = os.getenv("ALPACA_PAPER", "true").lower() == "false"

# OANDA — live forex trading (leave blank to use paper/simulated)
OANDA_TOKEN   = os.getenv("OANDA_TOKEN", "")
OANDA_ACCOUNT = os.getenv("OANDA_ACCOUNT", "")
OANDA_PAPER   = os.getenv("OANDA_PAPER", "true").lower() == "true"

# Crypto pairs
SYMBOLS = ["BTC/USDT", "ETH/USDT", "AVAX/USDT", "LINK/USDT", "ADA/USDT", "OP/USDT",
           "FET/USDT", "DYDX/USDT", "CRV/USDT", "BNB/USDT", "HBAR/USDT",
           "PENDLE/USDT", "MANA/USDT", "ETC/USDT", "JASMY/USDT", "SUSHI/USDT", "ALGO/USDT"]

# Stock symbols (NYSE/NASDAQ) — leave empty to disable
STOCK_SYMBOLS = ["NVDA", "SPY", "QQQ", "NFLX", "AMD", "WMT", "CRM", "V", "IWM",
                 "GS", "CVX", "SOXX", "BAC", "WEAT", "DBA", "DJP", "CAT", "XLI", "SCHD",
                 "MRK", "CB", "ROBO"]

# Forex pairs (24/5) — leave empty to disable
FOREX_SYMBOLS = ["EUR/USD", "GBP/USD", "AUD/USD"]
TIMEFRAME = "1h"
LIMIT = 210  # needs 200+ candles for trend filter EMA

# Active strategy: ema_crossover | rsi_reversal | macd_crossover | bollinger_reversion | combined
STRATEGY = "rsi_reversal"

# Trend filter: only allow buys when price is above this EMA length
TREND_FILTER = True
TREND_EMA_PERIOD = 200

# EMA crossover params
EMA_FAST = 9
EMA_SLOW = 21

# RSI params
RSI_PERIOD    = 10
RSI_OVERSOLD  = 25
RSI_OVERBOUGHT = 55

# MACD params
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger Bands params
BB_PERIOD = 20
BB_STD = 2.0

# Risk management
TRADE_AMOUNT_USDT = 10.0  # USDT per trade, per symbol
MAX_OPEN_TRADES = 1       # set to 1 while testing with small balance
TRAILING_STOP   = True    # stop moves up as price rises
STOP_LOSS_PCT   = 0.02    # trailing distance below highest price
TAKE_PROFIT_PCT = 0.04    # 4%

# Scheduler intervals (seconds)
POLL_INTERVAL       = 3600  # strategy signals — every 1 hour
SLTP_CHECK_INTERVAL = 300   # SL/TP price check — every 5 minutes
