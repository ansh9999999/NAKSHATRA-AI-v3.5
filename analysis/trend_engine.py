# analysis/trend_engine.py

from analysis.indicators import ema9, ema50, ema200, trend_strength


def analyze_trend(df, timeframe="5m"):
    """
    Analyze trend for a specific timeframe.
    Returns:
    {
        trend,
        score,
        reasons,
        ema9,
        ema50,
        ema200
    }
    """

    if df.empty or len(df) < 200:
        return {
            "trend": "UNKNOWN",
            "score": 0,
            "reasons": ["Not enough historical data"],
            "ema9": 0,
            "ema50": 0,
            "ema200": 0,
        }

    close = df["close"]

    ema9_value = float(ema9(close).iloc[-1])
    ema50_value = float(ema50(close).iloc[-1])
    ema200_value = float(ema200(close).iloc[-1])

    trend = trend_strength(close)

    score = 0
    reasons = []

    # Long-term trend
    if ema50_value > ema200_value:
        score += 20
        reasons.append(f"{timeframe}: EMA50 > EMA200")
    else:
        score -= 20
        reasons.append(f"{timeframe}: EMA50 < EMA200")

    # Entry trend
    if ema9_value > ema50_value:
        score += 15
        reasons.append(f"{timeframe}: EMA9 > EMA50")
    else:
        score -= 15
        reasons.append(f"{timeframe}: EMA9 < EMA50")

    # Trend strength
    if trend == "STRONG_BULL":
        score += 20
        reasons.append(f"{timeframe}: Strong Bull Trend")

    elif trend == "BULL":
        score += 10
        reasons.append(f"{timeframe}: Bull Trend")

    elif trend == "STRONG_BEAR":
        score -= 20
        reasons.append(f"{timeframe}: Strong Bear Trend")

    elif trend == "BEAR":
        score -= 10
        reasons.append(f"{timeframe}: Bear Trend")

    return {
        "trend": trend,
        "score": score,
        "reasons": reasons,
        "ema9": round(ema9_value, 2),
        "ema50": round(ema50_value, 2),
        "ema200": round(ema200_value, 2),
    }


def analyze_multi_timeframe(data):
    """
    data = {
        "5m": df,
        "15m": df,
        "1h": df,
        "1d": df,
        "1w": df,
        "1mo": df
    }
    """

    result = {}

    total_score = 0
    reasons = []

    for tf, df in data.items():
        analysis = analyze_trend(df, tf)
        result[tf] = analysis
        total_score += analysis["score"]
        reasons.extend(analysis["reasons"])

    result["total_score"] = total_score
    result["reasons"] = reasons

    return result
