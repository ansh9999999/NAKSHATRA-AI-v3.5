"""
NAKSHATRA AI
Decision Engine v5.0

Purpose:
- NO weighted scoring
- NO automatic BUY/SELL
- Present Technical, Astrology and Numerology separately
- Show whether all analyses agree
"""


def calculate_decision(
    technical_result,
    astrology_result,
    numerology_result
):

    # -----------------------------
    # Signals
    # -----------------------------

    technical_signal = (
        technical_result.get("signal", "NEUTRAL")
        .upper()
    )

    astrology_signal = (
        astrology_result.get("bias", "NEUTRAL")
        .upper()
    )

    numerology_signal = (
        numerology_result.get("bias", "NEUTRAL")
        .upper()
    )

    # -----------------------------
    # Agreement
    # -----------------------------

    signals = [
        technical_signal,
        astrology_signal,
        numerology_signal,
    ]

    unique = set(signals)

    if len(unique) == 1:

        agreement = "FULL AGREEMENT"

    elif len(unique) == 2:

        agreement = "PARTIAL AGREEMENT"

    else:

        agreement = "NO AGREEMENT"

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

    reasons = list(dict.fromkeys(reasons))

    # -----------------------------
    # Return
    # -----------------------------

    return {

        "technical": technical_result,

        "astrology": astrology_result,

        "numerology": numerology_result,

        "agreement": agreement,

        "technical_signal": technical_signal,

        "astrology_signal": astrology_signal,

        "numerology_signal": numerology_signal,

        "reasons": reasons

      }
