"""
NAKSHATRA AI
Lunar Engine
"""

from analysis.moon_phase import get_moon_phase
from analysis.nakshatra import get_nakshatra
from analysis.tithi import get_tithi
from analysis.rahu import get_rahu_kaal


def analyze_lunar(timestamp):

    moon = get_moon_phase(timestamp)

    nakshatra = get_nakshatra(timestamp)

    tithi = get_tithi(timestamp)

    rahu = get_rahu_kaal(timestamp)

    score = 0

    reasons = []

    if moon["bullish"]:
        score += 10
        reasons.append(moon["reason"])

    else:
        score -= 10

    if nakshatra["bullish"]:
        score += 10
        reasons.append(nakshatra["reason"])

    if tithi["bullish"]:
        score += 5
        reasons.append(tithi["reason"])

    if rahu["active"]:
        score -= 15
        reasons.append("Rahu Kaal Active")

    return {

        "score": score,

        "moon": moon,

        "nakshatra": nakshatra,

        "tithi": tithi,

        "rahu": rahu,

        "reasons": reasons

    }
