"""
NAKSHATRA AI
Decision Engine v5.2

Purpose:
- Normalize BUY/BULL and SELL/BEAR directions.
- Do not count NEUTRAL as directional agreement.
- Give Technical analysis the highest weight.
- Produce final direction, recommendation and confidence.
"""

def _normalize_direction(signal):
    """Convert all signal labels to BULLISH / BEARISH / NEUTRAL."""
    if not signal:
        return "NEUTRAL"

    value = str(signal).strip().upper()

    if value in ("BUY", "BULL", "BULLISH", "LONG"):
        return "BULLISH"

    if value in ("SELL", "BEAR", "BEARISH", "SHORT"):
        return "BEARISH"

    return "NEUTRAL"


def calculate_decision(
    technical_result,
    astrology_result,
    numerology_result
):
    technical_signal = technical_result.get("signal", "NEUTRAL")
    astrology_signal = astrology_result.get("bias", "NEUTRAL")
    numerology_signal = numerology_result.get("bias", "NEUTRAL")

    # Normalize labels before comparing directions.
    technical_direction = _normalize_direction(technical_signal)
    astrology_direction = _normalize_direction(astrology_signal)
    numerology_direction = _normalize_direction(numerology_signal)

    directions = [
        technical_direction,
        astrology_direction,
        numerology_direction,
    ]

    # -------------------------------------------------
    # Directional votes
    # -------------------------------------------------
    bullish_votes = directions.count("BULLISH")
    bearish_votes = directions.count("BEARISH")
    directional_votes = bullish_votes + bearish_votes

    # -------------------------------------------------
    # Agreement
    # NEUTRAL is NOT counted as agreement.
    # -------------------------------------------------
    if directional_votes == 0:
        agreement = "NO AGREEMENT"
    elif bullish_votes == 3 or bearish_votes == 3:
        agreement = "FULL AGREEMENT"
    elif bullish_votes >= 2 or bearish_votes >= 2:
        agreement = "PARTIAL AGREEMENT"
    else:
        agreement = "NO AGREEMENT"

    # -------------------------------------------------
    # Weighted directional score
    #
    # Technical = 60%
    # Astrology = 20%
    # Numerology = 20%
    #
    # Neutral contributes zero.
    # -------------------------------------------------
    weights = {
        "technical": 0.60,
        "astrology": 0.20,
        "numerology": 0.20,
    }

    weighted_score = 0.0

    if technical_direction == "BULLISH":
        weighted_score += weights["technical"]
    elif technical_direction == "BEARISH":
        weighted_score -= weights["technical"]

    if astrology_direction == "BULLISH":
        weighted_score += weights["astrology"]
    elif astrology_direction == "BEARISH":
        weighted_score -= weights["astrology"]

    if numerology_direction == "BULLISH":
        weighted_score += weights["numerology"]
    elif numerology_direction == "BEARISH":
        weighted_score -= weights["numerology"]

    # -------------------------------------------------
    # Confidence
    #
    # 0.00 -> 0%
    # +/-1.00 -> 100%
    #
    # Also include technical confidence so a weak
    # technical signal cannot look artificially strong.
    # -------------------------------------------------
    technical_confidence = float(
        technical_result.get("confidence", 0) or 0
    )
    technical_confidence = max(0.0, min(100.0, technical_confidence))

    direction_confidence = abs(weighted_score) * 100.0

    if directional_votes == 0:
        overall_confidence = 0.0
    else:
        # Technical analysis is the primary source.
        overall_confidence = (
            direction_confidence * 0.70
            + technical_confidence * 0.30
        )

    overall_confidence = max(
        0.0,
        min(100.0, overall_confidence)
    )

    # -------------------------------------------------
    # Final direction / recommendation
    #
    # Technical direction has priority when there is
    # a clear technical signal. A final trade is allowed
    # only when the weighted direction is sufficiently
    # strong.
    # -------------------------------------------------
    if weighted_score >= 0.60:
        final_direction = "BULLISH"
        recommendation = "BUY"

    elif weighted_score <= -0.60:
        final_direction = "BEARISH"
        recommendation = "SELL"

    else:
        final_direction = (
            "BULLISH" if weighted_score > 0
            else "BEARISH" if weighted_score < 0
            else "NEUTRAL"
        )
        recommendation = "WAIT"

    # If technical analysis is neutral, do not create a
    # trade solely from the two secondary modules.
    if technical_direction == "NEUTRAL":
        recommendation = "WAIT"

    # -------------------------------------------------
    # Reasons
    # -------------------------------------------------
    reasons = []

    reasons.extend(technical_result.get("reasons", []))
    reasons.extend(astrology_result.get("reasons", []))
    reasons.extend(numerology_result.get("reasons", []))

    reasons = list(dict.fromkeys(reasons))

    # Add transparent decision-engine explanations.
    reasons.append(
        f"Direction votes: Bullish={bullish_votes}, "
        f"Bearish={bearish_votes}, Neutral={3-directional_votes}"
    )
    reasons.append(
        f"Weighted score: {weighted_score:.2f}"
    )
    reasons.append(
        f"Technical confidence: {technical_confidence:.1f}%"
    )

    return {
        "recommendation": recommendation,
        "overall_confidence": round(overall_confidence, 1),

        "direction": final_direction,
        "agreement": agreement,

        "technical": technical_result,
        "astrology": astrology_result,
        "numerology": numerology_result,

        "normalized": {
            "technical": technical_direction,
            "astrology": astrology_direction,
            "numerology": numerology_direction,
        },

        "votes": {
            "bullish": bullish_votes,
            "bearish": bearish_votes,
            "neutral": 3 - directional_votes,
        },

        "weighted_score": round(weighted_score, 3),

        "reasons": reasons,
    }
