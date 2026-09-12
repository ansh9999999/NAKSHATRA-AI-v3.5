from config import SYMBOLS
from history import get_multi_timeframe_history

from analysis.signal import generate_signal

from telegram import send_message
from notify import send_notification

from logger import logger

last_alerts = {}


def create_message(result):
    """Create a notification only from a complete signal result.

    generate_signal() intentionally returns a small {recommendation, confidence}
    object when the 5m entry timeframe has no candles. The old scanner assumed
    technical/astrology/numerology always existed and crashed with KeyError.
    """
    if not isinstance(result, dict):
        return None

    if result.get("recommendation") == "NO DATA":
        return None

    technical = result.get("technical") or {}
    astrology = result.get("astrology") or {}
    numerology = result.get("numerology") or {}
    agreement = result.get("agreement")

    if isinstance(agreement, dict):
        bullish = agreement.get("bullish", 0)
        bearish = agreement.get("bearish", 0)
        agreement_text = "structured"
    else:
        bullish = "N/A"
        bearish = "N/A"
        agreement_text = str(agreement) if agreement is not None else "N/A"

    required = (technical, astrology, numerology)
    if not all(isinstance(item, dict) for item in required):
        return None

    msg = f"""
============================

NAKSHATRA AI

============================

Symbol : {result.get('symbol', 'UNKNOWN')}
Price : {result.get('price', 'N/A')}

--------------------------------
TECHNICAL ANALYSIS

Signal : {technical.get('signal', 'WAIT')}
Confidence : {technical.get('confidence', 0)}%

--------------------------------
ASTROLOGICAL ANALYSIS

Bias : {astrology.get('bias', 'NEUTRAL')}
Score : {astrology.get('score', 0)}%

--------------------------------
NUMEROLOGY ANALYSIS

Bias : {numerology.get('bias', 'NEUTRAL')}
Score : {numerology.get('score', 0)}%

--------------------------------
FINAL RECOMMENDATION

{result.get('recommendation', 'WAIT')}

Overall Confidence
{result.get('overall_confidence', 0)}%

Bullish Agreement
{bullish}/3

Bearish Agreement
{bearish}/3

Agreement
{agreement_text}

================================
"""

    return msg


def market_scan():
    logger.info("NAKSHATRA Scan Started")

    for symbol in SYMBOLS:
        try:
            data = get_multi_timeframe_history(symbol)

            if not data:
                logger.warning("%s: no multi-timeframe data", symbol)
                continue

            data["symbol"] = symbol
            result = generate_signal(data)

            # No 5m candles is a normal data-availability condition, not a
            # scanner exception. Do not attempt to format/send a full signal.
            if not isinstance(result, dict):
                logger.warning("%s: signal engine returned non-dict result", symbol)
                continue

            recommendation = result.get("recommendation", "NO DATA")

            if recommendation == "NO DATA":
                logger.warning("%s: scanner skipped because signal data is unavailable", symbol)
                continue

            if recommendation == "MIXED / MANUAL REVIEW":
                continue

            if last_alerts.get(symbol) == recommendation:
                continue

            message = create_message(result)
            if not message:
                logger.warning("%s: incomplete signal result; notification skipped", symbol)
                continue

            last_alerts[symbol] = recommendation

            logger.info(message)

            send_message(message)

            send_notification(
                title=f"{symbol} {recommendation}",
                message=message,
            )

        except Exception as exc:
            logger.exception(f"{symbol}: {exc}")

    logger.info("NAKSHATRA Scan Finished")


if __name__ == "__main__":
    market_scan()
