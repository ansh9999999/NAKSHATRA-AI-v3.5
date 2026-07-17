from analysis.indicators import ema, rsi, macd, atr
from analysis.adx import adx


def generate_signal(df):
    if df.empty or len(df) < 50:
        return {
            "signal": "WAIT",
            "score": 0,
            "reasons": ["Not enough data"]
        }

    close = df["close"]
    high = df["high"]
    low = df["low"]

    price = float(close.iloc[-1])

    ema9 = ema(close, 9).iloc[-1]
    ema21 = ema(close, 21).iloc[-1]

    rsi_value = rsi(close).iloc[-1]

    macd_line, signal_line, _ = macd(close)

    macd_value = macd_line.iloc[-1]
    signal_value = signal_line.iloc[-1]

    atr_value = atr(high, low, close).iloc[-1]
    adx_value = adx(high, low, close).iloc[-1]

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
    if 55 <= rsi_value <= 70:
        score += 15
        reasons.append("RSI Bullish")
    elif 30 <= rsi_value <= 45:
        score -= 15
        reasons.append("RSI Bearish")

    # MACD
    if macd_value > signal_value:
        score += 15
        reasons.append("MACD Bullish")
    else:
        score -= 15
        reasons.append("MACD Bearish")

    # ADX (trend strength)
    if adx_value >= 25:
        score += 10
        reasons.append("Strong Trend (ADX)")
    else:
        reasons.append("Weak Trend")

    # ATR (volatility)
    if atr_value > 0:
        score += 5
        reasons.append("ATR Normal")

    if score >= 40:
        signal = "BUY"
    elif score <= -40:
        signal = "SELL"
    else:
        signal = "WAIT"

    return {
        "signal": signal,
        "score": score,
        "price": round(price, 2),
        "ema9": round(float(ema9), 2),
        "ema21": round(float(ema21), 2),
        "rsi": round(float(rsi_value), 2),
        "adx": round(float(adx_value), 2),
        "atr": round(float(atr_value), 2),
        "reasons": reasons
    }
