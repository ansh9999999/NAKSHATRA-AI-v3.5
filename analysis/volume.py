import pandas as pd


def analyze_volume(df, period=20):

    if df.empty or len(df) < period:
        return {
            "score": 0,
            "status": "UNKNOWN",
            "reasons": ["Not enough data"]
        }

    current_volume = float(df["volume"].iloc[-1])
    avg_volume = float(df["volume"].tail(period).mean())

    score = 0
    reasons = []

    if current_volume > avg_volume * 1.5:
        score += 15
        status = "HIGH"
        reasons.append("High Volume Breakout")

    elif current_volume < avg_volume * 0.7:
        score -= 10
        status = "LOW"
        reasons.append("Low Volume")

    else:
        status = "NORMAL"
        reasons.append("Normal Volume")

    return {
        "status": status,
        "current_volume": round(current_volume, 2),
        "average_volume": round(avg_volume, 2),
        "score": score,
        "reasons": reasons
    }
