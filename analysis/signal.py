from analysis.indicators import (
    ema9,
    ema50,
    ema200,
    rsi,
    macd,
    atr,
    trend_strength
)

from analysis.adx import adx
from analysis.market_structure import analyze_market_structure
from analysis.volume import analyze_volume
from analysis.liquidity import analyze_liquidity


def generate_signal(df):

    if df.empty or len(df) < 200:

        return {
            "signal": "WAIT",
            "score": 0,
            "price": 0,
            "atr": 0,
            "reasons": ["Not enough historical data"]
        }

    close = df["close"]
    high = df["high"]
    low = df["low"]

    price = float(close.iloc[-1])

    # ==========================
    # EMA
    # ==========================

    ema9_value = float(ema9(close).iloc[-1])
    ema50_value = float(ema50(close).iloc[-1])
    ema200_value = float(ema200(close).iloc[-1])

    trend = trend_strength(close)

    # ==========================
    # RSI
    # ==========================

    rsi_value = float(rsi(close).iloc[-1])

    # ==========================
    # MACD
    # ==========================

    macd_line, signal_line, histogram = macd(close)

    macd_value = float(macd_line.iloc[-1])
    signal_value = float(signal_line.iloc[-1])

    # ==========================
    # ATR
    # ==========================

    atr_value = float(
        atr(high, low, close).iloc[-1]
    )

    # ==========================
    # ADX
    # ==========================

    adx_value = float(
        adx(high, low, close).iloc[-1]
    )

    # ==========================
    # Smart Money
    # ==========================

    structure = analyze_market_structure(df)

    volume = analyze_volume(df)

    liquidity = analyze_liquidity(df)

    score = 0

    reasons = []

    score += structure["score"]
    score += volume["score"]
    score += liquidity["score"]

    reasons.extend(structure["reasons"])
    reasons.extend(volume["reasons"])
    reasons.extend(liquidity["reasons"])

    # ==========================
    # Intraday EMA 9 / 50
    # ==========================

    if ema9_value > ema50_value:

        score += 20
        reasons.append("EMA 9 > EMA 50 (Intraday Bullish)")

    else:

        score -= 20
        reasons.append("EMA 9 < EMA 50 (Intraday Bearish)")

    # ==========================
    # Swing EMA 50 / 200
    # ==========================

    if ema50_value > ema200_value:

        score += 15
        reasons.append("EMA 50 > EMA 200 (Swing Bullish)")

    else:

        score -= 15
        reasons.append("EMA 50 < EMA 200 (Swing Bearish)")

    # ==========================
    # RSI
    # ==========================

    if 55 <= rsi_value <= 70:

        score += 15
        reasons.append("RSI Bullish")

    elif 30 <= rsi_value <= 45:

        score -= 15
        reasons.append("RSI Bearish")

    # ==========================
    # MACD
    # ==========================

    if macd_value > signal_value:

        score += 15
        reasons.append("MACD Bullish")

    else:

        score -= 15
        reasons.append("MACD Bearish")
            # ==========================
    # ADX
    # ==========================

    if adx_value >= 25:

        score += 10
        reasons.append("Strong Trend (ADX)")

    else:

        reasons.append("Weak Trend")

    # ==========================
    # ATR
    # ==========================

    if atr_value > 0:

        score += 5
        reasons.append("Healthy Volatility")

    # ==========================
    # Trend Strength
    # ==========================

    if trend == "STRONG_BULL":

        score += 20
        reasons.append("Strong Bull Trend")

    elif trend == "BULL":

        score += 10
        reasons.append("Bull Trend")

    elif trend == "STRONG_BEAR":

        score -= 20
        reasons.append("Strong Bear Trend")

    elif trend == "BEAR":

        score -= 10
        reasons.append("Bear Trend")

    # ==========================
    # Final Signal
    # ==========================

    confidence = min(abs(score), 100)

    if score >= 90:

        signal = "STRONG BUY"

    elif score >= 60:

        signal = "BUY"

    elif score <= -90:

        signal = "STRONG SELL"

    elif score <= -60:

        signal = "SELL"

    else:

        signal = "WAIT"

    return {

        "signal": signal,

        "confidence": confidence,

        "score": score,

        "price": round(price, 2),

        "ema9": round(ema9_value, 2),

        "ema50": round(ema50_value, 2),

        "ema200": round(ema200_value, 2),

        "rsi": round(rsi_value, 2),

        "adx": round(adx_value, 2),

        "atr": round(atr_value, 2),

        "trend": structure["trend"],

        "trend_strength": trend,

        "bos": structure["bos"],

        "choch": structure["choch"],

        "volume_status": volume["status"],

        "current_volume": volume["current_volume"],

        "average_volume": volume["average_volume"],

        "liquidity": liquidity["status"],

        "highest_high": liquidity["highest_high"],

        "lowest_low": liquidity["lowest_low"],

        "reasons": reasons

    }
