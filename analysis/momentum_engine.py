# analysis/momentum_engine.py

from analysis.indicators import rsi, macd, atr
from analysis.adx import adx


def analyze_momentum(df):
    """
    Momentum Analysis
    Returns:
    {
        score,
        reasons,
        rsi,
        macd,
        signal,
        adx,
        atr
    }
    """

    if df.empty or len(df) < 200:
        return {
            "score": 0,
            "reasons": ["Not enough historical data"],
            "rsi": 0,
            "macd": 0,
            "signal": 0,
            "adx": 0,
            "atr": 0,
        }

    close = df["close"]
    high = df["high"]
    low = df["low"]

    score = 0
    reasons = []

    # RSI
    rsi_value = float(rsi(close).iloc[-1])

    if 55 <= rsi_value <= 70:
        score += 15
        reasons.append("RSI Bullish")

    elif 30 <= rsi_value <= 45:
        score -= 15
        reasons.append("RSI Bearish")

    else:
        reasons.append("RSI Neutral")

    # MACD
    macd_line, signal_line, histogram = macd(close)

    macd_value = float(macd_line.iloc[-1])
    signal_value = float(signal_line.iloc[-1])

    if macd_value > signal_value:
        score += 15
        reasons.append("MACD Bullish")

    else:
        score -= 15
        reasons.append("MACD Bearish")

    # ADX
    adx_value = float(adx(high, low, close).iloc[-1])

    if adx_value >= 25:
        score += 10
        reasons.append("Strong Trend (ADX)")

    else:
        reasons.append("Weak Trend")

    # ATR
    atr_value = float(atr(high, low, close).iloc[-1])

    if atr_value > 0:
        score += 5
        reasons.append("Healthy Volatility")

    return {
        "score": score,
        "reasons": reasons,
        "rsi": round(rsi_value, 2),
        "macd": round(macd_value, 2),
        "signal": round(signal_value, 2),
        "adx": round(adx_value, 2),
        "atr": round(atr_value, 2),
  }
