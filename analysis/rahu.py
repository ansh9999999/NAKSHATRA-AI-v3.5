"""
NAKSHATRA AI
Rahu Kaal Engine
"""

from datetime import datetime, time


# --------------------------------------------------
# Default Rahu Kaal (Indian Standard Time)
# Placeholder values
# Future version will calculate dynamically
# --------------------------------------------------

RAHU_KAAL = {

    0: (time(7, 30), time(9, 0)),     # Monday

    1: (time(15, 0), time(16, 30)),   # Tuesday

    2: (time(12, 0), time(13, 30)),   # Wednesday

    3: (time(13, 30), time(15, 0)),   # Thursday

    4: (time(10, 30), time(12, 0)),   # Friday

    5: (time(9, 0), time(10, 30)),    # Saturday

    6: (time(16, 30), time(18, 0))    # Sunday

}


def get_rahu_kaal(timestamp):

    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    weekday = timestamp.weekday()

    start, end = RAHU_KAAL[weekday]

    current = timestamp.time()

    active = start <= current <= end

    score = -15 if active else 0

    if active:
        reason = "Rahu Kaal Active"
    else:
        reason = "Outside Rahu Kaal"

    return {

        "weekday": weekday,

        "start": start.strftime("%H:%M"),

        "end": end.strftime("%H:%M"),

        "active": active,

        "score": score,

        "reason": reason

    }


def get_all_rahu_timings():

    return {

        day: {

            "start": timing[0].strftime("%H:%M"),

            "end": timing[1].strftime("%H:%M")

        }

        for day, timing in RAHU_KAAL.items()

    }
