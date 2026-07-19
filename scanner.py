"""
NAKSHATRA AI
Market Scanner
"""

from config import SYMBOLS
from history import get_history
from analysis.signal import generate_signal
from risk.trade_manager import create_trade
from database.logger import log_trade
from telegram import send_message
from notify import send_notification
from logger import logger
from broker.manager import broker


# Prevent duplicate alerts
last_alerts = {}


def create_message(symbol, result, trade):
    """
    Build Telegram / ntfy message.
    """

    return f"""
🚀 NAKSHATRA AI

📊 Symbol : {symbol}

🎯 Signal : {trade['signal']}

💰 Entry : {trade['entry']}

🛑 Stop Loss : {trade['stop_loss']}

🎯 TP1 : {trade['tp1']}
🎯 TP2 : {trade['tp2']}
🎯 TP3 : {trade['tp3']}

📦 Quantity : {trade['quantity']}

⚖ Risk Reward : {trade['risk_reward']}

📈 Trend : {result['trend']}

📊 Volume : {result['volume_status']}

💧 Liquidity : {result['li
    def market_scan():
    """
    Main market scanning function.
    """

    logger.info("========== NAKSHATRA AI Scan Started ==========")

    for symbol in SYMBOLS:

        try:
            logger.info(f"Scanning {symbol}")

            df = get_history(symbol)

            if df.empty:
                logger.warning(f"{symbol}: No market data")
                continue

            result = generate_signal(df)

            signal = result.get("signal", "WAIT")

            if signal == "WAIT":
                logger.info(f"{symbol}: WAIT")
                continue

            if last_alerts.get(symbol) == signal:
                logger.info(f"{symbol}: Duplicate signal")
                continue

            last_alerts[symbol] = signal

            trade = create_trade(
                signal=signal,
                entry_price=result["price"],
                atr=result["atr"],
            )

            if trade is None:
                logger.warning(f"{symbol}: Trade creation failed")
                continue

            logger.info(f"{symbol}: Executing trade")

            order = execute_trade(
                symbol=symbol,
                signal=signal,
                trade=trade,
            )

            logger.info(f"{symbol}: Order -> {order}")

            try:
                log_trade(
                    symbol=symbol,
                    signal_data=result,
                    trade=trade,
                )
                logger.info(f"{symbol}: Trade logged")

            except Exception as db_error:
                logger.exception(f"{symbol}: Database Error: {db_error}")

            message = create_message(
                symbol,
                result,
                trade,
            )

            if send_message(message):
                logger.info(f"{symbol}: Telegram Sent")
            else:
                logger.warning(f"{symbol}: Telegram Failed")

            if send_notification(
                title=f"{symbol} {signal}",
                message=message,
            ):
                logger.info(f"{symbol}: ntfy Sent")
            else:
                logger.warning(f"{symbol}: ntfy Failed")

            logger.info(f"{symbol}: Scan Completed")

        except Exception as e:
            logger.exception(f"{symbol}: {e}")

    logger.info("========== NAKSHATRA AI Scan Finished ==========")

def broker_health():
    """
    Check broker connection.
    """

    try:
        return broker.health()

    except Exception as e:
        logger.exception(f"Broker Health Error: {e}")
        return False


if __name__ == "__main__":

    logger.info("Starting NAKSHATRA AI Scanner...")

    if broker_health():

        logger.info("Broker Connected Successfully")

        market_scan()

    else:

        logger.error("Broker Connection Failed")
