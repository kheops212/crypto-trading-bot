import config


def calculate_position_size(usdt_balance: float, price: float) -> float:
    budget = min(config.TRADE_AMOUNT_USDT, usdt_balance)
    return budget / price


def trailing_stop_price(highest_price: float) -> float:
    return highest_price * (1 - config.STOP_LOSS_PCT)


def stop_loss_price(entry_price: float) -> float:
    return entry_price * (1 - config.STOP_LOSS_PCT)


def take_profit_price(entry_price: float) -> float:
    return entry_price * (1 + config.TAKE_PROFIT_PCT)


def should_exit(current_price: float, entry_price: float, highest_price: float | None = None) -> str:
    """Returns 'stop_loss', 'take_profit', or 'hold'."""
    if config.TRAILING_STOP and highest_price is not None:
        if current_price <= trailing_stop_price(highest_price):
            return "stop_loss"
    else:
        if current_price <= stop_loss_price(entry_price):
            return "stop_loss"
    if current_price >= take_profit_price(entry_price):
        return "take_profit"
    return "hold"
