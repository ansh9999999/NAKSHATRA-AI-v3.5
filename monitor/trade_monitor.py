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
        return float(df.iloc[-1]["close"])
    except Exception as e:
        logger.exception(f"{symbol}: Price Fetch Error : {e}")
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

💵 PnL : {round(pnl, 2)}

📈 Result : {result}
"""

    send_message(message)

    send_notification(
        title=f"{symbol} {result}",
        message=message
    )

    logger.info(
        f"{symbol}: Trade Closed ({result})"
    )


def monitor_open_trades():
    """
    Monitor all active trades.
    """
