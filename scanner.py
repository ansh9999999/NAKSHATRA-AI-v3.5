from config import SYMBOLS, TIMEFRAME, CANDLE_LIMIT
from history import get_history
from analysis.signal import generate_signal
from telegram import send_message
from notify import send_notification
from logger import logger


last_alerts = {}


def scan_symbol(symbol):
    try:
        df = get_history(symbol, TIMEFRAME, CANDLE_LIMIT)

        result = generate_signal(df)

        signal = result["signal"]

        logger.info(f"{symbol} -> {signal}")

        if signal == "WAIT":
            return

        if last_alerts.get(symbol) == signal:
            logger.info(f"{symbol}: Duplicate alert skipped.")
            return

        last_alerts[symbol] = signal

        message = (
            f"{symbol}\n"
            f"Signal : {signal}\n"
            f"Price : {result['price']}\n"
            f"Score : {result['score']}\n"
            f"RSI : {result['rsi']}\n"
            f"EMA9 : {result['ema9']}\n"
            f"EMA21 : {result['ema21']}\n\n"
            f"Reasons:\n" +
            "\n".join(result["reasons"])
        )

        send_message(message)
        send_notification(f"{symbol} {signal}", message)

    except Exception as e:
        logger.exception(f"{symbol} scan failed: {e}")


def market_scan():
    logger.info("===== Market Scan Started =====")

    for symbol in SYMBOLS:
        scan_symbol(symbol)

    logger.info("===== Market Scan Finished =====")
