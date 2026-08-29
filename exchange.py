import ccxt
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from loguru import logger
import pytz
import config

_TF_MAP = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "60m", "4h": "60m", "1d": "1d"}
_FIAT   = {"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_stock(symbol: str) -> bool:
    return "/" not in symbol


def is_forex(symbol: str) -> bool:
    if "/" not in symbol:
        return False
    base, quote = symbol.split("/")
    return base in _FIAT and quote in _FIAT


def is_market_open() -> bool:
    """True when NYSE is open (9:30am–4:00pm ET, Mon–Fri)."""
    et = pytz.timezone("America/New_York")
    now = datetime.now(et)
    if now.weekday() >= 5:
        return False
    open_  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_ = now.replace(hour=16, minute=0,  second=0, microsecond=0)
    return open_ <= now <= close_


def is_forex_open() -> bool:
    """True when forex market is open (Sun 5pm – Fri 5pm ET)."""
    et  = pytz.timezone("America/New_York")
    now = datetime.now(et)
    wd  = now.weekday()   # 0=Mon … 6=Sun
    if wd == 5:           # Saturday — always closed
        return False
    if wd == 6:           # Sunday — open after 5pm ET
        return now.hour >= 17
    if wd == 4 and now.hour >= 17:  # Friday — closed after 5pm ET
        return False
    return True


# ---------------------------------------------------------------------------
# Simulated exchange — paper trading for crypto AND stocks via Yahoo Finance
# ---------------------------------------------------------------------------

class SimulatedExchange:
    def __init__(self, starting_usd: float = 1000.0):
        self._balances: dict[str, float] = {"USDT": starting_usd, "USD": starting_usd}
        logger.info(f"Simulated exchange ready (balance: ${starting_usd:,.2f})")

    def _yf_ticker(self, symbol: str) -> str:
        if is_stock(symbol):
            return symbol                          # AAPL, NVDA — already correct
        base, quote = symbol.split("/")
        if is_forex(symbol):
            return f"{base}{quote}=X"              # EUR/USD → EURUSD=X
        quote = "USD" if quote in ("USDT", "BUSD") else quote
        return f"{base}-{quote}"                   # BTC/USDT → BTC-USD

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        ticker = self._yf_ticker(symbol)
        yf_interval = _TF_MAP.get(timeframe, "60m")
        period = "7d" if yf_interval in ("1m", "5m", "15m") else "60d"
        raw = yf.download(ticker, period=period, interval=yf_interval,
                          auto_adjust=True, progress=False)
        if raw.empty:
            raise RuntimeError(f"No data returned for {ticker}")
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index.name = "timestamp"
        if timeframe == "4h":
            df = df.resample("4h").agg({
                "open": "first", "high": "max",
                "low": "min", "close": "last", "volume": "sum",
            }).dropna()
        return df.tail(limit)

    def get_balance(self, currency: str = "USDT") -> float:
        key = "USDT" if currency in ("USDT", "USD") else currency
        return self._balances.get(key, 0.0)

    def place_order(self, symbol: str, side: str, amount: float, price: float) -> dict:
        base = symbol.split("/")[0] if not is_stock(symbol) else symbol
        if side == "buy":
            self._balances["USDT"] = self._balances.get("USDT", 0.0) - amount * price
            self._balances["USD"]  = self._balances["USDT"]
            self._balances[base]   = self._balances.get(base, 0.0) + amount
        else:
            self._balances["USDT"] = self._balances.get("USDT", 0.0) + amount * price
            self._balances["USD"]  = self._balances["USDT"]
            self._balances[base]   = self._balances.get(base, 0.0) - amount
        logger.info(
            f"[SIM] {side.upper()} {amount:.6f} {symbol} @ ${price:,.2f} | "
            f"Cash: ${self._balances['USDT']:,.2f} | {base}: {self._balances.get(base, 0):.6f}"
        )
        return {"id": "sim", "side": side, "amount": amount, "price": price, "status": "closed"}


# ---------------------------------------------------------------------------
# Alpaca exchange — live stock trading
# ---------------------------------------------------------------------------

class AlpacaExchange:
    _PAPER_URL = "https://paper-api.alpaca.markets"
    _LIVE_URL  = "https://api.alpaca.markets"

    def __init__(self, key: str, secret: str, paper: bool = True):
        self._base = self._PAPER_URL if paper else self._LIVE_URL
        self._headers = {
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Content-Type": "application/json",
        }
        mode = "paper" if paper else "live"
        logger.info(f"Alpaca connected ({mode}): {self._base}")

    def _get(self, path: str) -> dict:
        r = requests.get(f"{self._base}{path}", headers=self._headers, timeout=15)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, payload: dict) -> dict:
        r = requests.post(f"{self._base}{path}", json=payload, headers=self._headers, timeout=15)
        r.raise_for_status()
        return r.json()

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        yf_interval = _TF_MAP.get(timeframe, "60m")
        raw = yf.download(symbol, period="60d", interval=yf_interval,
                          auto_adjust=True, progress=False)
        if raw.empty:
            raise RuntimeError(f"No data returned for {symbol}")
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index.name = "timestamp"
        return df.tail(limit)

    def get_balance(self, currency: str = "USD") -> float:
        account = self._get("/v2/account")
        return float(account.get("buying_power", 0.0))

    def place_order(self, symbol: str, side: str, amount: float, price: float) -> dict:
        order = self._post("/v2/orders", {
            "symbol": symbol,
            "qty": str(round(amount, 6)),
            "side": side,
            "type": "market",
            "time_in_force": "day",
        })
        logger.info(f"[ALPACA] {side.upper()} {amount:.6f} {symbol} @ ~${price:,.2f} | id={order.get('id')}")
        return order


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def connect():
    """Connect to crypto exchange."""
    if config.PAPER_TRADE:
        return SimulatedExchange(starting_usd=config.TRADE_AMOUNT_USDT * 10)
    exchange_class = getattr(ccxt, config.EXCHANGE)
    exchange = exchange_class({
        "apiKey": config.API_KEY,
        "secret": config.API_SECRET,
        "enableRateLimit": True,
    })
    logger.info(f"Connected to {config.EXCHANGE} (live)")
    return exchange


def connect_stocks():
    """Connect to stock exchange."""
    if config.PAPER_TRADE or not config.ALPACA_KEY:
        return SimulatedExchange(starting_usd=config.TRADE_AMOUNT_USDT * 10)
    return AlpacaExchange(config.ALPACA_KEY, config.ALPACA_SECRET, paper=config.ALPACA_PAPER)


def connect_forex():
    """Connect to forex exchange (OANDA for live, SimulatedExchange for paper)."""
    if config.PAPER_TRADE or not config.OANDA_TOKEN:
        return SimulatedExchange(starting_usd=config.TRADE_AMOUNT_USDT * 10)
    # OANDA live integration — placeholder for future implementation
    logger.warning("OANDA live trading not yet implemented — using simulated exchange.")
    return SimulatedExchange(starting_usd=config.TRADE_AMOUNT_USDT * 10)


def fetch_ohlcv(exchange, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    if isinstance(exchange, (SimulatedExchange, AlpacaExchange)):
        return exchange.fetch_ohlcv(symbol, timeframe, limit)
    raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


def get_balance(exchange, currency: str = "USDT") -> float:
    if isinstance(exchange, (SimulatedExchange, AlpacaExchange)):
        return exchange.get_balance(currency)
    balance = exchange.fetch_balance()
    return float(balance["free"].get(currency, 0.0))


def place_market_order(exchange, symbol: str, side: str, amount: float) -> dict:
    if isinstance(exchange, (SimulatedExchange, AlpacaExchange)):
        df = exchange.fetch_ohlcv(symbol, config.TIMEFRAME, 1)
        price = float(df["close"].iloc[-1])
        return exchange.place_order(symbol, side, amount, price)
    order = exchange.create_market_order(symbol, side, amount)
    logger.info(f"Order placed: {order}")
    return order
