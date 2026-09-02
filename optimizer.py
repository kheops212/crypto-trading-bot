"""
Auto-optimizer: runs RSI grid search weekly across all symbols and updates
RSI params if a better combination is found. Results saved to params.json.
"""
import json
import math
import warnings
import importlib
import pandas as pd
import pandas_ta as ta
import vectorbt as vbt
from pathlib import Path
from loguru import logger

import config
import trades

warnings.filterwarnings("ignore")

PARAMS_FILE    = Path(__file__).parent / "params.json"
RSI_PERIODS    = [7, 10, 14, 18, 21]
RSI_OVERSOLDS  = [20, 25, 30, 35]
RSI_OVERBOUGHTS = [55, 60, 65, 70, 75]

_FIAT = {"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"}


def _yf_ticker(symbol: str) -> str:
    if "/" not in symbol:
        return symbol
    base, quote = symbol.split("/")
    if base in _FIAT and quote in _FIAT:
        return f"{base}{quote}=X"
    quote = "USD" if quote in ("USDT", "BUSD") else quote
    return f"{base}-{quote}"


def _score(win_rate: float, trades_count: int, max_dd: float) -> float:
    if trades_count < 2:
        return 0.0
    return (win_rate / 100) * math.log(trades_count + 1) - (max_dd / 100) * 0.3


def load_params() -> dict:
    if PARAMS_FILE.exists():
        try:
            return json.loads(PARAMS_FILE.read_text())
        except Exception:
            pass
    return {}


def save_params(params: dict):
    PARAMS_FILE.write_text(json.dumps(params, indent=2))


def run_optimization() -> dict:
    """
    Grid search RSI params across a sample of symbols using 3 months of data.
    Returns the best param combo as a dict, or {} if no valid result found.
    """
    all_symbols = (config.SYMBOLS + config.STOCK_SYMBOLS + config.FOREX_SYMBOLS)
    sample = all_symbols[:12]  # cap at 12 symbols to keep runtime under ~2 min

    combo_scores: dict[tuple, list] = {}

    for symbol in sample:
        ticker = _yf_ticker(symbol)
        try:
            price = vbt.YFData.download(
                ticker, period="3mo", interval="1h"
            ).get("Close").squeeze()
            if len(price) < 100:
                continue
            df = pd.DataFrame({"close": price})

            for rp in RSI_PERIODS:
                rsi = ta.rsi(df["close"], length=rp)
                for ob in RSI_OVERBOUGHTS:
                    for os_ in RSI_OVERSOLDS:
                        if os_ >= ob:
                            continue
                        entries = (rsi >= os_) & (rsi.shift(1) < os_)
                        exits   = (rsi <= ob)  & (rsi.shift(1) > ob)
                        entries = entries.fillna(False)
                        exits   = exits.fillna(False)
                        if entries.sum() < 2:
                            continue
                        try:
                            pf = vbt.Portfolio.from_signals(
                                price, entries, exits, init_cash=1000, fees=0.001
                            )
                            s  = pf.stats()
                            wr = s.get("Win Rate [%]") or 0
                            dd = s.get("Max Drawdown [%]") or 100
                            tc = int(s.get("Total Trades") or 0)
                            sc = _score(wr, tc, dd)
                            key = (rp, os_, ob)
                            combo_scores.setdefault(key, []).append(sc)
                        except Exception:
                            pass
        except Exception:
            pass

    # Only keep combos that worked on at least 2 symbols
    valid = {k: sum(v) / len(v) for k, v in combo_scores.items() if len(v) >= 2}
    if not valid:
        return {}

    best_key = max(valid, key=valid.get)
    rp, os_, ob = best_key
    return {
        "RSI_PERIOD":    rp,
        "RSI_OVERSOLD":  os_,
        "RSI_OVERBOUGHT": ob,
        "score":         round(valid[best_key], 4),
    }


def optimize_and_apply() -> bool:
    """
    Run the grid search and save new params if they differ from current.
    Reloads the config module so changes take effect immediately.
    Returns True if params changed.
    """
    logger.info("Auto-optimizer: starting weekly RSI grid search (this may take ~2 min)...")

    new = run_optimization()
    if not new:
        logger.warning("Auto-optimizer: no valid results — keeping current params.")
        return False

    current = {
        "RSI_PERIOD":    config.RSI_PERIOD,
        "RSI_OVERSOLD":  config.RSI_OVERSOLD,
        "RSI_OVERBOUGHT": config.RSI_OVERBOUGHT,
    }

    changed = (
        new["RSI_PERIOD"]     != current["RSI_PERIOD"]    or
        new["RSI_OVERSOLD"]   != current["RSI_OVERSOLD"]  or
        new["RSI_OVERBOUGHT"] != current["RSI_OVERBOUGHT"]
    )

    save_params(new)
    importlib.reload(config)

    if changed:
        msg = (
            f"RSI_PERIOD {current['RSI_PERIOD']} → {new['RSI_PERIOD']} | "
            f"Oversold {current['RSI_OVERSOLD']} → {new['RSI_OVERSOLD']} | "
            f"Overbought {current['RSI_OVERBOUGHT']} → {new['RSI_OVERBOUGHT']} | "
            f"Score: {new['score']}"
        )
        logger.info(f"Auto-optimizer: params updated! {msg}")
        trades.log_notification(
            title="RSI params auto-updated",
            body=msg,
            level="info",
        )
    else:
        logger.info(
            f"Auto-optimizer: current params are still optimal "
            f"(score={new['score']})"
        )

    return changed
