"""
NAKSHATRA AI
Numerology Engine v4.0
"""

from datetime import datetime


def digital_root(number):

    while number > 9:
        number = sum(int(i) for i in str(number))

    return number


def analyze_numerology(timestamp, symbol="BTCUSD"):

    """
    Returns

    {
        bias,
        score,
        reasons
    }
    """

    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    # -----------------------------
    # Universal Day Number
    # -----------------------------

    total = (
        timestamp.day +
        timestamp.month +
        timestamp.year
    )

    day_number = digital_root(total)

    score = 50
    bias = "NEUTRAL"

    reasons = []

    # -----------------------------
    # Universal Day
    # -----------------------------

    if day_number in [1, 3, 5, 8]:

        score += 20
        bias = "POSITIVE"

        reasons.append(
            f"Universal Day Number {day_number} is positive"
        )

    elif day_number in [4, 7]:

        score -= 15

        reasons.append(
            f"Universal Day Number {day_number} indicates caution"
        )

    elif day_number in [2, 6, 9]:

        score += 10

        reasons.append(
            f"Universal Day Number {day_number} is supportive"
        )

    # -----------------------------
    # Symbol Vibration
    # -----------------------------

    symbol = symbol.upper()

    if "BTC" in symbol:

        score += 5

        reasons.append(
            "BTC vibration bonus"
        )

    elif "ETH" in symbol:

        score += 5

        reasons.append(
            "ETH vibration bonus"
        )

    # -----------------------------
    # Clamp
    # -----------------------------

    score = max(0, min(100, score))

    if score >= 70:
        bias = "POSITIVE"

    elif score <= 35:
        bias = "NEGATIVE"

    return {

        "bias": bias,

        "score": score,

        "reasons": reasons,

        "details": {

            "day_number": day_number,

            "symbol": symbol

        }

    }
