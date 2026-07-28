# analysis/confidence_engine.py

"""
NAKSHATRA AI
Confidence Engine v4.0
"""

TECHNICAL_WEIGHT = 60
ASTROLOGY_WEIGHT = 25
NUMEROLOGY_WEIGHT = 15


def calculate_confidence(
    technical_result,
    astrology_result,
    numerology_result
):

    # -----------------------------
    # Scores
    # -----------------------------

    technical_score = max(
        0,
        min(100, technical_result.get("confidence", 0))
    )

    astrology_score = max(
        0,
        min(100, astrology_result.get("score", 0))
    )

    numerology_score = max(
        0,
        min(100, numerology_result.get("score", 0))
    )

    # -----------------------------
    # Weighted Confidence
    # -----------------------------

    overall_confidence = round(
        (
            technical_score * TECHNICAL_WEIGHT
            + astrology_score * ASTROLOGY_WEIGHT
            + numerology_score * NUMEROLOGY_WEIGHT
        ) / 100,
        2
    )

    # -----------------------------
    # Agreement
    # -----------------------------

    bullish = 0
    bearish = 0

    if "BUY" in technical_result.get("signal", "").upper():
        bullish += 1

    elif "SELL" in technical_result.get("signal", "").upper():
        bearish += 1

    if astrology_result.get("bias", "").upper() == "BULLISH":
        bullish += 1

    elif astrology_result.get("bias", "").upper() == "BEARISH":
        bearish += 1

    if numerology_result.get("bias", "").upper() == "POSITIVE":
        bullish += 1

    elif numerology_result.get("bias", "").upper() == "NEGATIVE":
        bearish += 1

    # -----------------------------
    # Final Recommendation
    # -----------------------------

    if bullish == 3:
        recommendation = "STRONG BUY"

    elif bullish == 2:
        recommendation = "BUY BIAS"

    elif bearish == 3:
        recommendation = "STRONG SELL"

    elif bearish == 2:
        recommendation = "SELL BIAS"

    else:
        recommendation = "MIXED / MANUAL REVIEW"

    # -----------------------------
    # Reasons
    # -----------------------------

    reasons = []

    reasons.extend(
        technical_result.get("reasons", [])
    )

    reasons.extend(
        astrology_result.get("reasons", [])
    )

    reasons.extend(
        numerology_result.get("reasons", [])
    )

    # -----------------------------
    # Return
    # -----------------------------

    return {

        "technical": technical_result,

        "astrology": astrology_result,

        "numerology": numerology_result,

        "technical_score": technical_score,

        "astrology_score": astrology_score,

        "numerology_score": numerology_score,

        "overall_confidence": overall_confidence,

        "recommendation": recommendation,

        "agreement": {
            "bullish": bullish,
            "bearish": bearish
        },

        "reasons": reasons
    }
