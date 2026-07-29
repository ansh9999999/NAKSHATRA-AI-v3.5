# analysis/momentum_engine.py

from analysis.indicators import (
    rsi,
    macd,
    atr,
    vwap,
    volume_sma,
)

from analysis.adx import adx


def analyze_momentum(df):

    if df.empty or len(df) < 200:
        return {
            "score": 0,
            "reasons": ["Not enough historical data"],
            "rsi": 0,
            "macd": 0,
            "signal": 0,
            "adx": 0,
            "atr": 0,
            "vwap": 0,
            "volume_ratio": 0,
        }

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    score = 0
    reasons = []

    # RSI
    rsi_value = float(rsi(close).iloc[-1])

    if rsi_value >= 60:
        score += 15
        reasons.append("RSI Bullish")

    elif rsi_value <= 40:
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

    # VWAP
    vwap_value = float(vwap(high, low, close, volume).iloc[-1])

    if close.iloc[-1] > vwap_value:
        score += 10
        reasons.append("Price Above VWAP")
    else:
        score -= 10
        reasons.append("Price Below VWAP")

    # Volume
    avg_volume = float(volume_sma(volume, 20).iloc[-1])

    if avg_volume > 0:
        volume_ratio = float(volume.iloc[-1] / avg_volume)
    else:
        volume_ratio = 0

    if volume_ratio >= 1.5:
        score += 10
        reasons.append("High Volume Confirmation")
    elif volume_ratio < 0.8:
        score -= 5
        reasons.append("Low Volume")

    return {

        "score": score,

        "reasons": reasons,

        "rsi": round(rsi_value, 2),

        "macd": round(macd_value, 2),

        "signal": round(signal_value, 2),

        "adx": round(adx_value, 2),

        "atr": round(atr_value, 2),

        "vwap": round(vwap_value, 2),

        "volume_ratio": round(volume_ratio, 2),
    }
