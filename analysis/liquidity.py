import pandas as pd


def analyze_liquidity(df, lookback=20):

    if df.empty or len(df) < lookback + 1:
        return {
            "status": "UNKNOWN",
            "score": 0,
            "highest_high": None,
            "lowest_low": None,
            "reasons": ["Not enough data"]
        }

    recent = df.tail(lookback + 1)

    # Previous candles only
    history = recent.iloc[:-1]

    # Current candle
    last = recent.iloc[-1]

    highest_high = float(history["high"].max())
    lowest_low = float(history["low"].min())

    avg_volume = float(history["volume"].mean())
    current_volume = float(last["volume"])

    score = 0
    reasons = []

    status = "NONE"

    # -----------------------------
    # Bullish Liquidity Sweep
    # -----------------------------
    if (
        last["low"] < lowest_low
        and last["close"] > lowest_low
    ):

        status = "BULLISH_SWEEP"

        score += 20
        reasons.append("Bullish Liquidity Sweep")

        if current_volume > avg_volume * 1.2:
            score += 5
            reasons.append("High Volume Confirmation")

    # -----------------------------
    # Bearish Liquidity Sweep
    # -----------------------------
    elif (
        last["high"] > highest_high
        and last["close"] < highest_high
    ):

        status = "BEARISH_SWEEP"

        score -= 20
        reasons.append("Bearish Liquidity Sweep")

        if current_volume > avg_volume * 1.2:
            score -= 5
            reasons.append("High Volume Confirmation")

    else:
        reasons.append("No Liquidity Sweep")

    return {

        "status": status,

        "highest_high": round(highest_high, 2),

        "lowest_low": round(lowest_low, 2),

        "current_volume": round(current_volume, 2),

        "average_volume": round(avg_volume, 2),

        "score": score,

        "reasons": reasons

    }
