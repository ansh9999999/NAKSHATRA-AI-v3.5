"""
NAKSHATRA AI
Tithi Engine
"""

from datetime import datetime


TITHIS = [

    "Shukla Pratipada",
    "Shukla Dwitiya",
    "Shukla Tritiya",
    "Shukla Chaturthi",
    "Shukla Panchami",
    "Shukla Shashthi",
    "Shukla Saptami",
    "Shukla Ashtami",
    "Shukla Navami",
    "Shukla Dashami",
    "Shukla Ekadashi",
    "Shukla Dwadashi",
    "Shukla Trayodashi",
    "Shukla Chaturdashi",
    "Purnima",

    "Krishna Pratipada",
    "Krishna Dwitiya",
    "Krishna Tritiya",
    "Krishna Chaturthi",
    "Krishna Panchami",
    "Krishna Shashthi",
    "Krishna Saptami",
    "Krishna Ashtami",
    "Krishna Navami",
    "Krishna Dashami",
    "Krishna Ekadashi",
    "Krishna Dwadashi",
    "Krishna Trayodashi",
    "Krishna Chaturdashi",
    "Amavasya"

]


BULLISH = {

    "Shukla Panchami",
    "Shukla Saptami",
    "Shukla Dashami",
    "Shukla Ekadashi",
    "Shukla Dwadashi"

}


BEARISH = {

    "Krishna Chaturdashi",
    "Amavasya"

}


NEUTRAL = {

    "Purnima"

}


def get_tithi(timestamp):

    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    # -------------------------------------
    # Temporary Logic
    # Will be replaced by Swiss Ephemeris
    # -------------------------------------

    index = (timestamp.day - 1) % 30

    name = TITHIS[index]

    bullish = False

    score = 0

    reason = "Neutral Tithi"

    if name in BULLISH:

        bullish = True

        score = 5

        reason = "Historically Positive Tithi"

    elif name in BEARISH:

        bullish = False

        score = -5

        reason = "Historically Weak Tithi"

    elif name in NEUTRAL:

        bullish = False

        score = 0

        reason = "High Volatility"

    return {

        "name": name,

        "bullish": bullish,

        "score": score,

        "reason": reason

    }


def get_all_tithis():

    return TITHIS
