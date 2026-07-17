from analysis.indicators import ema, rsi, macd


def generate_signal(df):
    if df.empty or len(df) < 50:
        return {
            "signal": "WAIT",
            "score": 0,
            "reasons": ["Not enough data"]
        }

    close = df["close"]

    ema9 = ema(close, 9).iloc[-1]
    ema21 = ema(close, 21).iloc[-1]

    rsi_value = rsi(close).iloc[-1]

    macd_line, signal_line, _ = macd(close)

    macd_value = macd_line.iloc[-1]
    signal_value = signal_line.iloc[-1]

    score = 0
    reasons = []

    # EMA
    if ema9 > ema21:
        score += 20
        reasons.append("EMA Bullish")
    else:
        score -= 20
        reasons.append("EMA Bearish")

    # RSI
    if 58 <= rsi_value <= 72:
        score += 15
        reasons.append("RSI Bullish")
    elif 28 <= rsi_value <= 42:
        score -= 15
        reasons.append("RSI Bearish")

    # MACD
    if macd_value > signal_value:
        score += 15
        reasons.append("MACD Bullish")
    else:
        score -= 15
        reasons.append("MACD Bearish")

    if score >= 40:
        signal = "BUY"
    elif score <= -40:
        signal = "SELL"
    else:
        signal = "WAIT"

    return {
        "signal": signal,
        "score": score,
        "price": float(close.iloc[-1]),
        "ema9": round(float(ema9), 2),
        "ema21": round(float(ema21), 2),
        "rsi": round(float(rsi_value), 2),
        "reasons": reasons
    }
