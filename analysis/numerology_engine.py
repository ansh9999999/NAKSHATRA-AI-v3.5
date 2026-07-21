"""
NAKSHATRA AI
Numerology Engine
"""

from datetime import datetime


def reduce_number(number):

    while number > 9 and number not in (11, 22, 33):
        number = sum(int(d) for d in str(number))

    return number


def get_universal_day(timestamp):

    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    total = (
        timestamp.day +
        timestamp.month +
        timestamp.year
    )

    return reduce_number(total)


def get_symbol_number(symbol):

    symbol = symbol.upper()

    total = 0

    for ch in symbol:

        if "A" <= ch <= "Z":
            total += ord(ch) - 64

        elif ch.isdigit():
            total += int(ch)

    return reduce_number(total)


def analyze_numerology(timestamp, symbol="BTCUSD"):

    day = get_universal_day(timestamp)

    symbol_no = get_symbol_number(symbol)

    score = 0

    reasons = []

    if day in [1, 3, 5, 8]:

        score += 5

        reasons.append(f"Universal Day {day} Positive")

    elif day in [4, 7]:

        score -= 5

        reasons.append(f"Universal Day {day} Weak")

    if symbol_no in [1, 5, 8]:

        score += 5

        reasons.append(f"Symbol Number {symbol_no} Strong")

    return {

        "universal_day": day,

        "symbol_number": symbol_no,

        "score": score,

        "reasons": reasons

    }
