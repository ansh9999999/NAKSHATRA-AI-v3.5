import pandas as pd


def swing_high(df, lookback=3):
    highs = []

    for i in range(lookback, len(df) - lookback):

        current = df["high"].iloc[i]

        if current == max(df["high"].iloc[i-lookback:i+lookback+1]):
            highs.append((i, current))

    return highs


def swing_low(df, lookback=3):
    lows = []

    for i in range(lookback, len(df) - lookback):

        current = df["low"].iloc[i]

        if current == min(df["low"].iloc[i-lookback:i+lookback+1]):
            lows.append((i, current))

    return lows


def detect_trend(df):

    highs = swing_high(df)
    lows = swing_low(df)

    if len(highs) < 2 or len(lows) < 2:
        return "SIDEWAYS"

    last_high = highs[-1][1]
    prev_high = highs[-2][1]

    last_low = lows[-1][1]
    prev_low = lows[-2][1]

    if last_high > prev_high and last_low > prev_low:
        return "UPTREND"

    if last_high < prev_high and last_low < prev_low:
        return "DOWNTREND"

    return "SIDEWAYS"


def detect_bos(df):

    trend = detect_trend(df)

    close = df["close"].iloc[-1]

    highs = swing_high(df)
    lows = swing_low(df)

    if len(highs) == 0 or len(lows) == 0:
        return False

    if trend == "UPTREND":

        return close > highs[-1][1]

    if trend == "DOWNTREND":

        return close < lows[-1][1]

    return False


def detect_choch(df):

    trend = detect_trend(df)

    close = df["close"].iloc[-1]

    highs = swing_high(df)
    lows = swing_low(df)

    if len(highs) == 0 or len(lows) == 0:
        return False

    if trend == "UPTREND":

        return close < lows[-1][1]

    if trend == "DOWNTREND":

        return close > highs[-1][1]

    return False


def analyze_market_structure(df):

    trend = detect_trend(df)

    bos = detect_bos(df)

    choch = detect_choch(df)

    score = 0

    reasons = []

    if trend == "UPTREND":

        score += 20

        reasons.append("Uptrend")

    elif trend == "DOWNTREND":

        score -= 20

        reasons.append("Downtrend")

    else:

        reasons.append("Sideways")

    if bos:

        if trend == "UPTREND":

            score += 15

            reasons.append("Bullish BOS")

        elif trend == "DOWNTREND":

            score -= 15

            reasons.append("Bearish BOS")

    if choch:

        reasons.append("CHOCH Detected")

    return {

        "trend": trend,

        "bos": bos,

        "choch": choch,

        "score": score,

        "reasons": reasons

  }
