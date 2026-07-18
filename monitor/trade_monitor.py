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

from notify import send_notification

from logger import logger

from broker.manager import broker


def get_current_price(symbol):
    """
    Fetch latest market price.
    """

    try:

        df = get_history(symbol)

        if df.empty:
            return None

        return float(
            df.iloc[-1]["close"]
        )

    except Exception as e:

        logger.exception(
            f"{symbol}: Price Fetch Error : {e}"
        )

        return None


def close_trade(
    trade_id,
    symbol,
    signal,
    entry,
    exit_price,
    pnl,
    result
):
    """
    Close trade and update database.
    """

    update_trade(
        trade_id,
        exit_price,
        pnl,
        result
    )

    message = f"""
✅ Trade Closed

📊 Symbol : {symbol}

🎯 Signal : {signal}

💰 Entry : {entry}

🏁 Exit : {exit_price}

💵 PnL : {round(pnl,2)}

📈 Result : {result}
"""

    send_message(message)

    send_notification(
        title=f"{symbol} {result}",
        message=message
    )

    logger.info(
        f"{symbol}: Trade Closed ({result})"
        def monitor_open_trades():
    """
    Monitor all active trades.
    """

    trades = get_open_trades()

    if not trades:

        logger.info("No Open Trades")

        return

    logger.info(
        f"Monitoring {len(trades)} Open Trades"
    )

    for trade in trades:

        try:

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

            try:

                broker.close_position(

                    symbol=symbol,

                    side=signal.lower(),

                    quantity=None,

                    exit_price=exit_price

                )

            except Exception as broker_error:

                logger.exception(

                    f"{symbol}: Broker Close Error : {broker_error}"

                )

            close_trade(

                trade_id=trade_id,

                symbol=symbol,

                signal=signal,

                entry=entry,

                exit_price=exit_price,

                pnl=pnl,

                result=result

            )

        except Exception as e:

            logger.exception(

                f"Trade Monitor Error : {e}"

        )
        def broker_health():
    """
    Check broker connection.
    """

    try:

        return broker.health()

    except Exception as e:

        logger.exception(
            f"Broker Health Error : {e}"
        )

        return False


def monitor():
    """
    Main monitor entry point.
    """

    logger.info(
        "========== NAKSHATRA AI Trade Monitor =========="
    )

    if not broker_health():

        logger.error(
            "Broker connection failed."
        )

        return

    monitor_open_trades()

    logger.info(
        "========== Monitor Finished =========="
    )


if __name__ == "__main__":

    monitor()
    
    )
