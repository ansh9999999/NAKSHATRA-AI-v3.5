"""
NAKSHATRA AI
Moon Phase Engine
"""

from datetime import datetime


def get_moon_phase(timestamp):

    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    day = timestamp.day

    phase = "UNKNOWN"
    bullish = False
    reason = ""

    # Temporary Logic
    # Swiss Ephemeris integration will replace this

    if day in [13, 14, 15]:
        phase = "FULL MOON"
        bullish = False
        reason = "Full Moon - High Emotional Volatility"

    elif day in [28, 29, 30, 1]:
        phase = "NEW MOON"
        bullish = True
        reason = "New Moon - Fresh Trend Potential"

    elif 2 <= day <= 7:
        phase = "WAXING CRESCENT"
        bullish = True
        reason = "Bullish Momentum Building"

    elif 8 <= day <= 12:
        phase = "FIRST QUARTER"
        bullish = True
        reason = "Trend Continuation"

    elif 16 <= day <= 21:
        phase = "WANING GIBBOUS"
        bullish = False
        reason = "Profit Booking Zone"

    elif 22 <= day <= 27:
        phase = "LAST QUARTER"
        bullish = False
        reason = "Weak Momentum"

    return {

        "phase": phase,

        "bullish": bullish,

        "reason": reason

  }
