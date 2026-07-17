from config import SYMBOLS, TIMEFRAME, CANDLE_LIMIT
from history import get_history
from analysis.signal import generate_signal
from telegram import send_message
from notify import send_notification
from logger import logger

last_alerts = {}


def scan_symbol(symbol):
    try:
        logger.info(f"Scanning {symbol}")

        df = get_history(
            symbol=symbol,
            resolution=TIMEFRAME,
            limit=CANDLE_LIMIT
        )

        if df.empty:
            logger.warning(f"{symbol}: No candle data received.")
            return

        result = generate_signal(df)

        signal = result["signal"]

        logger.info(
            f"{symbol} | {signal} | Score={result['score']}"
        )

        if signal == "WAIT":
            return

        if last_alerts.get(symbol) == signal:
            logger.info(f"{symbol}: Duplicate signal skipped.")
            return

        last_alerts[symbol] = signal

        message = (
            f"📊 NAKSHATRA AI v3.5\n\n"
            f"Symbol : {symbol}\n"
            f"Signal : {signal}\n"
            f"Price : {result['price']}\n"
            f"Score : {result['score']}\n\n"
            f"EMA9 : {result['ema9']}\n"
            f"EMA21 : {result['ema21']}\n"
            f"RSI : {result['rsi']}\n"
            f"ADX : {result['adx']}\n"
            f"ATR : {result['atr']}\n\n"
            f"Reasons:\n"
            + "\n".join(f"• {reason}" for reason in result["reasons"])
        )

        tg = send_message(message)

        if tg:
            logger.info(f"{symbol}: Telegram sent.")
        else:
            logger.warning(f"{symbol}: Telegram failed.")

        ntfy = send_notification(
            f"{symbol} {signal}",
            message
        )

        if ntfy:
            logger.info(f"{symbol}: ntfy sent.")
        else:
            logger.warning(f"{symbol}: ntfy failed.")

    except Exception as e:
        logger.exception(f"{symbol} Scan Error: {e}")


def market_scan():
    logger.info("===================================")
    logger.info("NAKSHATRA AI Market Scan Started")
    logger.info("===================================")

    for symbol in SYMBOLS:
        scan_symbol(symbol)

    logger.info("Market Scan Finished")
