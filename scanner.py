from config import SYMBOLS
from logger import logger

from telegram import send_message
from notify import send_notification

from analysis.timeframe import (
    analyze_timeframes,
    final_decision,
)

last_alerts = {}


def scan_symbol(symbol):

    try:

        logger.info(f"Scanning {symbol}")

        results = analyze_timeframes(symbol)

        decision = final_decision(results)

        signal = decision["decision"]

        score = decision["score"]

        logger.info(
            f"{symbol} | {signal} | Score={score}"
        )

        if signal == "WAIT":

            logger.info(
                f"{symbol}: Waiting..."
            )

            return

        if last_alerts.get(symbol) == signal:

            logger.info(
                f"{symbol}: Duplicate Signal Skipped."
            )

            return

        last_alerts[symbol] = signal

        message = (
            "📊 NAKSHATRA AI v4\n\n"

            f"Symbol : {symbol}\n"
            f"Decision : {signal}\n"
            f"Score : {score}\n\n"

            "Multi Timeframe\n"

            f"5m  : {results['5m']['signal']} ({results['5m']['score']})\n"
            f"15m : {results['15m']['signal']} ({results['15m']['score']})\n"
            f"1h  : {results['1h']['signal']} ({results['1h']['score']})\n"
            f"4h  : {results['4h']['signal']} ({results['4h']['score']})"
        )

        tg = send_message(message)

        if tg:
            logger.info(
                f"{symbol}: Telegram Sent"
            )
        else:
            logger.warning(
                f"{symbol}: Telegram Failed"
            )

        ntfy = send_notification(
            f"{symbol} {signal}",
            message
        )

        if ntfy:
            logger.info(
                f"{symbol}: NTFY Sent"
            )
        else:
            logger.warning(
                f"{symbol}: NTFY Failed"
            )

    except Exception as e:

        logger.exception(
            f"{symbol} Scan Error : {e}"
        )


def market_scan():

    logger.info("================================")
    logger.info("NAKSHATRA AI v4")
    logger.info("Market Scan Started")
    logger.info("================================")

    for symbol in SYMBOLS:

        scan_symbol(symbol)

    logger.info("================================")
    logger.info("Market Scan Finished")
    logger.info("================================")
