from config import SYMBOLS
from history import get_multi_timeframe_history

from analysis.signal import generate_signal

from telegram import send_message
from notify import send_notification

from logger import logger

last_alerts = {}


def create_message(result):

    technical = result["technical"]
    astrology = result["astrology"]
    numerology = result["numerology"]

    msg = f"""
============================

NAKSHATRA AI

============================

Symbol : {result['symbol']}

Price : {result['price']}

--------------------------------

TECHNICAL ANALYSIS

Signal : {technical['signal']}

Confidence : {technical['confidence']}%

--------------------------------

ASTROLOGICAL ANALYSIS

Bias : {astrology['bias']}

Score : {astrology['score']}%

--------------------------------

NUMEROLOGY ANALYSIS

Bias : {numerology['bias']}

Score : {numerology['score']}%

--------------------------------

FINAL RECOMMENDATION

{result['recommendation']}

Overall Confidence

{result['overall_confidence']}%

Bullish Agreement

{result['agreement']['bullish']}/3

Bearish Agreement

{result['agreement']['bearish']}/3

================================
"""

    return msg


def market_scan():

    logger.info("NAKSHATRA Scan Started")

    for symbol in SYMBOLS:

        try:

            data = get_multi_timeframe_history(symbol)

            if not data:
                continue

            result = generate_signal(data)

            recommendation = result["recommendation"]

            if recommendation == "MIXED / MANUAL REVIEW":
                continue

            if last_alerts.get(symbol) == recommendation:
                continue

            last_alerts[symbol] = recommendation

            message = create_message(result)

            logger.info(message)

            send_message(message)

            send_notification(

                title=f"{symbol} {recommendation}",

                message=message

            )

        except Exception as e:

            logger.exception(f"{symbol}: {e}")

    logger.info("NAKSHATRA Scan Finished")


if __name__ == "__main__":

    market_scan()
