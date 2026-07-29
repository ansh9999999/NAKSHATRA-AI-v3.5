"""
NAKSHATRA AI
Decision Engine v5.1
"""


def calculate_decision(
    technical_result,
    astrology_result,
    numerology_result
):

    technical_signal = technical_result.get("signal", "NEUTRAL")
    astrology_signal = astrology_result.get("bias", "NEUTRAL")
    numerology_signal = numerology_result.get("bias", "NEUTRAL")

    agreement = "NO AGREEMENT"

    if (
        technical_signal == astrology_signal
        == numerology_signal
    ):
        agreement = "FULL AGREEMENT"

    elif (
        technical_signal == astrology_signal
        or technical_signal == numerology_signal
        or astrology_signal == numerology_signal
    ):
        agreement = "PARTIAL AGREEMENT"

    reasons = []

    reasons.extend(technical_result.get("reasons", []))
    reasons.extend(astrology_result.get("reasons", []))
    reasons.extend(numerology_result.get("reasons", []))

    reasons = list(dict.fromkeys(reasons))

    return {

        "agreement": agreement,

        "technical": technical_result,

        "astrology": astrology_result,

        "numerology": numerology_result,

        "reasons": reasons

    }
