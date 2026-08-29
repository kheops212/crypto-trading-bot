"""
Backtest any strategy against 6 months of BTC-USD hourly data.
Run: python backtest.py [strategy_name]
Available: ema_crossover, rsi_reversal, macd_crossover, bollinger_reversion, combined
"""
import sys
import pandas as pd
import pandas_ta as ta
import vectorbt as vbt
import config

STRATEGY = sys.argv[1] if len(sys.argv) > 1 else config.STRATEGY


def build_signals(price: pd.Series) -> tuple[pd.Series, pd.Series]:
    df = pd.DataFrame({"close": price})

    if STRATEGY == "ema_crossover":
        df["fast"] = ta.ema(df["close"], length=config.EMA_FAST)
        df["slow"] = ta.ema(df["close"], length=config.EMA_SLOW)
        entries = (df["fast"] > df["slow"]) & (df["fast"].shift(1) <= df["slow"].shift(1))
        exits = (df["fast"] < df["slow"]) & (df["fast"].shift(1) >= df["slow"].shift(1))

    elif STRATEGY == "rsi_reversal":
        df["rsi"] = ta.rsi(df["close"], length=config.RSI_PERIOD)
        entries = (df["rsi"] >= config.RSI_OVERSOLD) & (df["rsi"].shift(1) < config.RSI_OVERSOLD)
        exits = (df["rsi"] <= config.RSI_OVERBOUGHT) & (df["rsi"].shift(1) > config.RSI_OVERBOUGHT)

    elif STRATEGY == "macd_crossover":
        macd = ta.macd(df["close"], fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
        df["macd"] = macd.filter(like="MACD_").iloc[:, 0]
        df["sig"] = macd.filter(like="MACDs_").iloc[:, 0]
        entries = (df["macd"] > df["sig"]) & (df["macd"].shift(1) <= df["sig"].shift(1))
        exits = (df["macd"] < df["sig"]) & (df["macd"].shift(1) >= df["sig"].shift(1))

    elif STRATEGY == "bollinger_reversion":
        bb = ta.bbands(df["close"], length=config.BB_PERIOD, std=config.BB_STD)
        df["lower"] = bb.filter(like="BBL_").iloc[:, 0]
        df["upper"] = bb.filter(like="BBU_").iloc[:, 0]
        entries = df["close"] < df["lower"]
        exits = df["close"] > df["upper"]

    elif STRATEGY == "combined":
        macd = ta.macd(df["close"], fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
        df["macd"] = macd.filter(like="MACD_").iloc[:, 0]
        df["sig"] = macd.filter(like="MACDs_").iloc[:, 0]
        df["rsi"] = ta.rsi(df["close"], length=config.RSI_PERIOD)
        macd_cross_up = (df["macd"] > df["sig"]) & (df["macd"].shift(1) <= df["sig"].shift(1))
        macd_cross_dn = (df["macd"] < df["sig"]) & (df["macd"].shift(1) >= df["sig"].shift(1))
        entries = macd_cross_up & (df["rsi"] < config.RSI_OVERBOUGHT)
        exits = macd_cross_dn & (df["rsi"] > config.RSI_OVERSOLD)

    else:
        raise ValueError(f"Unknown strategy: {STRATEGY}")

    return entries.fillna(False), exits.fillna(False)


def run():
    print(f"Downloading BTC-USD 1h data (6 months)...")
    price = vbt.YFData.download("BTC-USD", period="6mo", interval="1h").get("Close")

    print(f"Running backtest: {STRATEGY}")
    entries, exits = build_signals(price)

    portfolio = vbt.Portfolio.from_signals(
        price,
        entries,
        exits,
        init_cash=1000,
        fees=0.001,
    )

    print(f"\n{'='*40}")
    print(f"Strategy: {STRATEGY}")
    print(f"{'='*40}")
    print(portfolio.stats())
    portfolio.plot().show()


if __name__ == "__main__":
    run()
