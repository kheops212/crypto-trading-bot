import pandas as pd
import pandas_ta as ta
import config


# ---------------------------------------------------------------------------
# Indicator helpers
# ---------------------------------------------------------------------------

def _with_ema(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema_fast"] = ta.ema(df["close"], length=config.EMA_FAST)
    df["ema_slow"] = ta.ema(df["close"], length=config.EMA_SLOW)
    return df


def _with_rsi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rsi"] = ta.rsi(df["close"], length=config.RSI_PERIOD)
    return df


def _with_macd(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    macd = ta.macd(df["close"], fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
    if macd is None:
        df["macd"] = float("nan")
        df["macd_signal"] = float("nan")
        return df
    df["macd"] = macd.filter(like="MACD_").iloc[:, 0]
    df["macd_signal"] = macd.filter(like="MACDs_").iloc[:, 0]
    return df


def _with_bbands(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    bb = ta.bbands(df["close"], length=config.BB_PERIOD, std=config.BB_STD)
    df["bb_lower"] = bb.filter(like="BBL_").iloc[:, 0]
    df["bb_upper"] = bb.filter(like="BBU_").iloc[:, 0]
    df["bb_mid"] = bb.filter(like="BBM_").iloc[:, 0]
    return df


# ---------------------------------------------------------------------------
# Strategy 1: EMA Crossover
# Buy when fast EMA crosses above slow EMA, sell on cross below.
# ---------------------------------------------------------------------------

def ema_crossover(df: pd.DataFrame) -> str:
    df = _with_ema(df).dropna()
    if len(df) < 2:
        return "hold"
    prev, curr = df.iloc[-2], df.iloc[-1]
    if prev["ema_fast"] <= prev["ema_slow"] and curr["ema_fast"] > curr["ema_slow"]:
        return "buy"
    if prev["ema_fast"] >= prev["ema_slow"] and curr["ema_fast"] < curr["ema_slow"]:
        return "sell"
    return "hold"


# ---------------------------------------------------------------------------
# Strategy 2: RSI Oversold/Overbought
# Buy when RSI crosses up through oversold level, sell when it crosses down
# through overbought level.
# ---------------------------------------------------------------------------

def rsi_reversal(df: pd.DataFrame) -> str:
    df = _with_rsi(df).dropna()
    if len(df) < 2:
        return "hold"
    prev, curr = df.iloc[-2], df.iloc[-1]
    if prev["rsi"] < config.RSI_OVERSOLD and curr["rsi"] >= config.RSI_OVERSOLD:
        return "buy"
    if prev["rsi"] > config.RSI_OVERBOUGHT and curr["rsi"] <= config.RSI_OVERBOUGHT:
        return "sell"
    return "hold"


# ---------------------------------------------------------------------------
# Strategy 3: MACD Signal Line Crossover
# Buy when MACD line crosses above signal line, sell on cross below.
# ---------------------------------------------------------------------------

def macd_crossover(df: pd.DataFrame) -> str:
    df = _with_macd(df).dropna()
    if len(df) < 2:
        return "hold"
    prev, curr = df.iloc[-2], df.iloc[-1]
    if prev["macd"] <= prev["macd_signal"] and curr["macd"] > curr["macd_signal"]:
        return "buy"
    if prev["macd"] >= prev["macd_signal"] and curr["macd"] < curr["macd_signal"]:
        return "sell"
    return "hold"


# ---------------------------------------------------------------------------
# Strategy 4: Bollinger Band Mean Reversion
# Buy when price closes below lower band (oversold), sell when it closes
# above upper band (overbought).
# ---------------------------------------------------------------------------

def bollinger_reversion(df: pd.DataFrame) -> str:
    df = _with_bbands(df).dropna()
    if len(df) < 1:
        return "hold"
    curr = df.iloc[-1]
    if curr["close"] < curr["bb_lower"]:
        return "buy"
    if curr["close"] > curr["bb_upper"]:
        return "sell"
    return "hold"


# ---------------------------------------------------------------------------
# Strategy 5: Combined Confirmation
# Requires RSI + MACD to agree before acting — reduces false signals.
# ---------------------------------------------------------------------------

def combined(df: pd.DataFrame) -> str:
    df = _with_rsi(_with_macd(df)).dropna()
    if len(df) < 2:
        return "hold"
    prev, curr = df.iloc[-2], df.iloc[-1]

    macd_bullish = prev["macd"] <= prev["macd_signal"] and curr["macd"] > curr["macd_signal"]
    macd_bearish = prev["macd"] >= prev["macd_signal"] and curr["macd"] < curr["macd_signal"]
    rsi_not_overbought = curr["rsi"] < config.RSI_OVERBOUGHT
    rsi_not_oversold = curr["rsi"] > config.RSI_OVERSOLD

    if macd_bullish and rsi_not_overbought:
        return "buy"
    if macd_bearish and rsi_not_oversold:
        return "sell"
    return "hold"


# ---------------------------------------------------------------------------
# Router — called by main.py
# ---------------------------------------------------------------------------

STRATEGIES = {
    "ema_crossover": ema_crossover,
    "rsi_reversal": rsi_reversal,
    "macd_crossover": macd_crossover,
    "bollinger_reversion": bollinger_reversion,
    "combined": combined,
}


def _trend_is_up(df: pd.DataFrame) -> bool:
    """Returns True when price is above the 200 EMA (uptrend)."""
    ema200 = ta.ema(df["close"], length=config.TREND_EMA_PERIOD)
    if ema200 is None or ema200.isna().all():
        return True  # not enough data — don't block
    return float(df["close"].iloc[-1]) > float(ema200.iloc[-1])


def get_signal(df: pd.DataFrame) -> str:
    fn = STRATEGIES.get(config.STRATEGY)
    if fn is None:
        raise ValueError(f"Unknown strategy '{config.STRATEGY}'. Choose from: {list(STRATEGIES)}")
    signal = fn(df)
    if signal == "buy" and config.TREND_FILTER and not _trend_is_up(df):
        return "hold"  # suppress buy in downtrend
    return signal
