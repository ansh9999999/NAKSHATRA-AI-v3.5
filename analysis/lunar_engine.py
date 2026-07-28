"""
NAKSHATRA AI
Lunar Engine v4.0
"""

from datetime import datetime


def analyze_lunar(timestamp):

    """
    Returns:

    {
        bias,
        score,
        reasons
    }
    """

    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    day = timestamp.day

    score = 50
    bias = "NEUTRAL"
    reasons = []

    # --------------------------------
    # Example Logic
    # (Temporary)
    # --------------------------------

    if 1 <= day <= 5:

        score += 20
        bias = "BULLISH"

        reasons.append(
            "Early lunar cycle supports bullish momentum"
        )

    elif 13 <= day <= 17:

        score += 15

        reasons.append(
            "Full moon zone may increase volatility"
        )

    elif 27 <= day <= 30:

        score -= 20
        bias = "BEARISH"

        reasons.append(
            "End of lunar cycle indicates weakness"
        )

    # ------------------------------

    score = max(0, min(100, score))

    if score >= 70 and bias == "NEUTRAL":
        bias = "BULLISH"

    elif score <= 35:
        bias = "BEARISH"

    return {

        "bias": bias,

        "score": score,

        "reasons": reasons,

        "details": {

            "day": day

        }

    }
