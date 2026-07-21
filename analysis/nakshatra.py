"""
NAKSHATRA AI
Nakshatra Engine
"""

from datetime import datetime


NAKSHATRAS = [

    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati"

]


BULLISH = {

    "Ashwini",
    "Rohini",
    "Pushya",
    "Hasta",
    "Anuradha",
    "Shravana",
    "Revati"

}


BEARISH = {

    "Ardra",
    "Ashlesha",
    "Jyeshtha",
    "Mula"

}


def get_nakshatra(timestamp):

    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    # -----------------------------------
    # Temporary Placeholder
    # Swiss Ephemeris integration later
    # -----------------------------------

    index = timestamp.day % 27

    name = NAKSHATRAS[index]

    bullish = False

    score = 0

    reason = "Neutral Nakshatra"

    if name in BULLISH:

        bullish = True

        score = 10

        reason = "Historically Bullish Nakshatra"

    elif name in BEARISH:

        bullish = False

        score = -10

        reason = "Historically Weak Nakshatra"

    return {

        "name": name,

        "bullish": bullish,

        "score": score,

        "reason": reason

    }


def get_all_nakshatras():

    return NAKSHATRAS
