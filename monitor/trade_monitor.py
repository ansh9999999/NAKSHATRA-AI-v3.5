"""
NAKSHATRA AI
Trade Monitor
"""

from database.models import (
    get_open_trades,
    update_trade,
)

from history import get_history

from telegram import send_message

from logger import logger


def get_current_price(symbol):

    df = get_history(symbol)

    if df.empty:
        return None

    return float(df.iloc[-1]["close"])


def monitor_open_trades():

    trades = get_open_trades()

    if not trades:
        logger.info("No Open Trades")
        return

    logger.info(f"Monitoring {len(trades)} Open Trades")

    for trade in trades:

        trade_id = trade[0]

        symbol = trade[2]

        signal = trade[3]

        entry = float(trade[4])

        stop = float(trade[5])

        target = float(trade[6])

        current = get_current_price(symbol)

        if current is None:
            continue

        result = None
        exit_price = current
        pnl = 0

        if signal in ["BUY", "STRONG BUY"]:

            if current >= target:
                result = "WIN"
                exit_price = target

            elif current <= stop:
                result = "LOSS"
                exit_price = stop

            pnl = exit_price - entry

        elif signal in ["SELL", "STRONG SELL"]:

            if current <= target:
                result = "WIN"
                exit_price = target

            elif current >= stop:
                result = "LOSS"
                exit_price = stop

            pnl = entry - exit_price

        if result is None:
            continue

        update_trade(
            trade_id,
            exit_price,
            pnl,
            result
        )

        message = f"""
✅ Trade Closed

Symbol : {symbol}

Signal : {signal}

Entry : {entry}

Exit : {exit_price}

PnL : {round(pnl,2)}

Result : {result}
"""

        send_message(message)

        logger.info(
            f"{symbol} {result} PnL={round(pnl,2)}"
        )


if __name__ == "__main__":
    monitor_open_trades()
