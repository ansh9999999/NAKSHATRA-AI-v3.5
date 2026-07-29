"""
NAKSHATRA AI
Astrology Engine v5.0
"""

from analysis.moon_phase import analyze_moon_phase
from analysis.nakshatra import analyze_nakshatra
from analysis.tithi import analyze_tithi
from analysis.rahu import analyze_rahu


def analyze_astrology(timestamp):

    moon = analyze_moon_phase(timestamp)
    nakshatra = analyze_nakshatra(timestamp)
    tithi = analyze_tithi(timestamp)
    rahu = analyze_rahu(timestamp)

    score = 0
    reasons = []

    score += moon.get("score", 0)
    score += nakshatra.get("score", 0)
    score += tithi.get("score", 0)
    score += rahu.get("score", 0)

    score = round(score / 4)

    reasons.extend(moon.get("reasons", []))
    reasons.extend(nakshatra.get("reasons", []))
    reasons.extend(tithi.get("reasons", []))
    reasons.extend(rahu.get("reasons", []))

    reasons = list(dict.fromkeys(reasons))

    if score >= 70:
        bias = "BULLISH"
    elif score <= 35:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    return {

        "bias": bias,

        "score": score,

        "moon": moon,

        "nakshatra": nakshatra,

        "tithi": tithi,

        "rahu": rahu,

        "reasons": reasons

  }
