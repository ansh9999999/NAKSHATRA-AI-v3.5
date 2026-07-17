import pandas as pd


def analyze_liquidity(df, lookback=20):

    if df.empty or len(df) < lookback:
        return {
            "status": "UNKNOWN",
            "score": 0,
            "reasons": ["Not enough data"]
        }

    recent = df.tail(lookback)

    highest_high = recent["high"].max()
    lowest_low = recent["low"].min()

    last = recent.iloc[-1]

    score = 0
    reasons = []

    status = "NONE"

    # Bullish Liquidity Sweep
    if last["low"] < lowest_low and last["close"] > lowest_low:
        score += 20
        status = "BULLISH_SWEEP"
        reasons.append("Bullish Liquidity Sweep")

    # Bearish Liquidity Sweep
    elif last["high"] > highest_high and last["close"] < highest_high:
        score -= 20
        status = "BEARISH_SWEEP"
        reasons.append("Bearish Liquidity Sweep")

    else:
        reasons.append("No Liquidity Sweep")

    return {

        "status": status,

        "highest_high": round(float(highest_high),2),

        "lowest_low": round(float(lowest_low),2),

        "score": score,

        "reasons": reasons

    }
