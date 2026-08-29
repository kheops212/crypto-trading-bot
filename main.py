import time
from loguru import logger
import config
import exchange as ex
import strategy
import risk
import trades
import notifier


def _notify(title: str, body: str, level: str):
    trades.log_notification(title=title, body=body, level=level)
    notifier.send(title=title, body=body, level=level)


def _open_position(exchange, symbol: str, price: float, amount: float):
    sl = risk.stop_loss_price(price)
    tp = risk.take_profit_price(price)
    ex.place_market_order(exchange, symbol, "buy", amount)
    trades.open_position(symbol, amount, price, sl, tp, config.STRATEGY)
    trades.log_trade(symbol, "buy", amount, price, config.STRATEGY)
    _notify(
        title=f"BUY {symbol}",
        body=f"Bought {amount:.6f} @ ${price:,.2f} | SL: ${sl:,.2f} | TP: ${tp:,.2f} | Strategy: {config.STRATEGY}",
        level="success",
    )
    logger.info(f"BUY {amount:.6f} {symbol} @ ${price:,.2f} | SL ${sl:,.2f} | TP ${tp:,.2f}")


def _close_position(exchange, position: dict, price: float, reason: str):
    ex.place_market_order(exchange, position["symbol"], "sell", position["amount"])
    trades.close_position(position["id"], price, reason)
    trades.log_trade(position["symbol"], "sell", position["amount"], price, reason)
    pnl = (price - position["entry_price"]) * position["amount"]
    pnl_pct = (price / position["entry_price"] - 1) * 100
    level = "success" if pnl >= 0 else "error"
    _notify(
        title=f"CLOSED {position['symbol']} [{reason}]",
        body=(
            f"Sold {position['amount']:.6f} @ ${price:,.2f} | "
            f"Entry: ${position['entry_price']:,.2f} | "
            f"P&L: {pnl:+.4f} ({pnl_pct:+.2f}%)"
        ),
        level=level,
    )
    logger.info(f"CLOSE {position['symbol']} @ ${price:,.2f} | reason={reason} | P&L={pnl:+.4f} ({pnl_pct:+.2f}%)")


# ---------------------------------------------------------------------------
# Startup: warn about positions whose symbol is no longer in the watchlist
# ---------------------------------------------------------------------------

def check_orphaned_positions():
    all_symbols = set(config.SYMBOLS + config.STOCK_SYMBOLS)
    orphaned = [p for p in trades.get_all_open_positions() if p["symbol"] not in all_symbols]
    if not orphaned:
        return
    for p in orphaned:
        logger.warning(
            f"ORPHANED POSITION: {p['symbol']} | amount={p['amount']:.6f} | "
            f"entry=${p['entry_price']:,.2f} | SL=${p['stop_loss']:,.2f} | TP=${p['take_profit']:,.2f} | "
            f"opened={p['opened_at'][:19]}"
        )
    _notify(
        title=f"{len(orphaned)} orphaned position(s) detected",
        body="\n".join(
            f"{p['symbol']}: entry=${p['entry_price']:,.2f} TP=${p['take_profit']:,.2f} — not in watchlist"
            for p in orphaned
        ),
        level="warning",
    )


# ---------------------------------------------------------------------------
# Fast loop: SL/TP check on open positions only (every 5 min)
# ---------------------------------------------------------------------------

def check_sltp(crypto_exchange, stock_exchange, forex_exchange):
    open_positions = trades.get_all_open_positions()
    if not open_positions:
        return
    for position in open_positions:
        symbol = position["symbol"]
        try:
            if ex.is_stock(symbol) and not ex.is_market_open():
                continue
            if ex.is_forex(symbol) and not ex.is_forex_open():
                continue
            if ex.is_stock(symbol):
                exchange = stock_exchange
            elif ex.is_forex(symbol):
                exchange = forex_exchange
            else:
                exchange = crypto_exchange
            df = ex.fetch_ohlcv(exchange, symbol, config.TIMEFRAME, 1)
            current_price = float(df["close"].iloc[-1])

            # Update trailing high-water mark
            highest = position.get("highest_price") or position["entry_price"]
            if current_price > highest:
                highest = current_price
                trades.update_highest_price(position["id"], highest)
                trail_stop = risk.trailing_stop_price(highest)
                logger.info(
                    f"[{symbol}] New high ${highest:,.2f} → trailing stop raised to ${trail_stop:,.2f}"
                )

            exit_reason = risk.should_exit(current_price, position["entry_price"], highest)
            if exit_reason != "hold":
                logger.info(f"[{symbol}] {exit_reason} triggered @ ${current_price:,.2f}")
                _close_position(exchange, position, current_price, exit_reason)
        except Exception as e:
            logger.error(f"[{symbol}] SL/TP check error: {e}")


# ---------------------------------------------------------------------------
# Hourly loop: strategy signals → new entries and strategy-driven exits
# ---------------------------------------------------------------------------

def run_symbol(exchange, symbol: str):
    df = ex.fetch_ohlcv(exchange, symbol, config.TIMEFRAME, config.LIMIT)
    current_price = float(df["close"].iloc[-1])
    signal = strategy.get_signal(df)

    logger.info(f"[{symbol}] Signal: {signal} | Price: ${current_price:,.2f}")

    position = trades.get_open_position(symbol)
    if position:
        if signal == "sell":
            _close_position(exchange, position, current_price, "strategy_signal")
            return
        pnl_pct = (current_price / position["entry_price"] - 1) * 100
        logger.info(
            f"[{symbol}] Holding {position['amount']:.6f} | "
            f"Entry: ${position['entry_price']:,.2f} | "
            f"SL: ${position['stop_loss']:,.2f} | TP: ${position['take_profit']:,.2f} | "
            f"P&L: {pnl_pct:+.2f}%"
        )
        return

    open_count = len(trades.get_all_open_positions())
    if open_count >= config.MAX_OPEN_TRADES:
        logger.info(f"[{symbol}] Global cap reached ({config.MAX_OPEN_TRADES} open), skipping.")
        return

    if signal == "buy":
        quote = "USDT" if not ex.is_stock(symbol) and not ex.is_forex(symbol) else "USD"
        balance = ex.get_balance(exchange, quote)
        amount = risk.calculate_position_size(balance, current_price)
        if amount > 0:
            _open_position(exchange, symbol, current_price, amount)
        else:
            logger.warning(f"[{symbol}] Insufficient balance.")
            _notify(
                title=f"Buy skipped — {symbol}",
                body=f"Insufficient balance @ ${current_price:,.2f}",
                level="warning",
            )
    else:
        logger.info(f"[{symbol}] No trade this cycle.")


def run_bot(crypto_exchange, stock_exchange, forex_exchange):
    logger.info(
        f"--- Strategy cycle | {len(config.SYMBOLS)} crypto + "
        f"{len(config.STOCK_SYMBOLS)} stocks + {len(config.FOREX_SYMBOLS)} forex ---"
    )
    for symbol in config.SYMBOLS:
        try:
            run_symbol(crypto_exchange, symbol)
        except Exception as e:
            logger.error(f"[{symbol}] Error: {e}")

    if config.STOCK_SYMBOLS:
        if ex.is_market_open():
            for symbol in config.STOCK_SYMBOLS:
                try:
                    run_symbol(stock_exchange, symbol)
                except Exception as e:
                    logger.error(f"[{symbol}] Error: {e}")
        else:
            logger.info("Stock market closed — skipping stocks.")

    if config.FOREX_SYMBOLS:
        if ex.is_forex_open():
            for symbol in config.FOREX_SYMBOLS:
                try:
                    run_symbol(forex_exchange, symbol)
                except Exception as e:
                    logger.error(f"[{symbol}] Error: {e}")
        else:
            logger.info("Forex market closed — skipping forex.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    logger.add("bot.log", rotation="10 MB", retention="7 days")
    trades.init_db()

    crypto_exchange = ex.connect()
    stock_exchange  = ex.connect_stocks()
    forex_exchange  = ex.connect_forex()

    check_orphaned_positions()

    logger.info(
        f"Bot started | Strategy: {config.STRATEGY} | "
        f"Crypto: {config.SYMBOLS} | Stocks: {config.STOCK_SYMBOLS} | "
        f"Forex: {config.FOREX_SYMBOLS} | Paper: {config.PAPER_TRADE} | "
        f"SL/TP check: {config.SLTP_CHECK_INTERVAL}s | Strategy: {config.POLL_INTERVAL}s"
    )

    last_strategy_run = 0
    while True:
        now = time.time()

        # Fast SL/TP check every 5 minutes
        check_sltp(crypto_exchange, stock_exchange, forex_exchange)

        # Full strategy run every hour
        if now - last_strategy_run >= config.POLL_INTERVAL:
            run_bot(crypto_exchange, stock_exchange, forex_exchange)
            last_strategy_run = now

        time.sleep(config.SLTP_CHECK_INTERVAL)


if __name__ == "__main__":
    main()
