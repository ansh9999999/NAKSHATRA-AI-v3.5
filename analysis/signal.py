"""
NAKSHATRA AI
Master Signal Engine v4.0
"""

from analysis.trend_engine import analyze_multi_timeframe
from analysis.momentum_engine import analyze_momentum
from analysis.smart_money_engine import analyze_smart_money
from analysis.confidence_engine import calculate_confidence

from analysis.lunar_engine import analyze_lunar
from analysis.numerology_engine import analyze_numerology


def generate_signal(data):

    # ---------------------------------
    # Entry Timeframe
    # ---------------------------------

    entry_df = data["5m"]

    if entry_df.empty:
        return {
            "recommendation": "NO DATA",
            "overall_confidence": 0
        }

    # ---------------------------------
    # Technical Engines
    # ---------------------------------

    trend_result = analyze_multi_timeframe(data)

    momentum_result = analyze_momentum(entry_df)

    smart_money_result = analyze_smart_money(entry_df)

    # ---------------------------------
    # Technical Score
    # ---------------------------------

    technical_score = (
        trend_result["total_score"]
        + momentum_result["score"]
        + smart_money_result["score"]
    )

    technical_score = max(0, min(100, abs(technical_score)))

    # ---------------------------------
    # Technical Signal
    # ---------------------------------

    if technical_score >= 85:
        technical_signal = "BUY"

    elif technical_score <= 25:
        technical_signal = "SELL"

    else:
        technical_signal = "NEUTRAL"

    technical_result = {

        "signal": technical_signal,

        "confidence": technical_score,

        "trend": trend_result,

        "momentum": momentum_result,

        "smart_money": smart_money_result,

        "reasons":
            trend_result["reasons"]
            + momentum_result["reasons"]
            + smart_money_result["reasons"]
    }

    # ---------------------------------
    # Time
    # ---------------------------------

    timestamp = entry_df.index[-1]

    if hasattr(timestamp, "to_pydatetime"):
        timestamp = timestamp.to_pydatetime()

    symbol = data.get("symbol", "BTCUSD")

    # ---------------------------------
    # Astrology
    # ---------------------------------

    astrology_result = analyze_lunar(timestamp)

    # ---------------------------------
    # Numerology
    # ---------------------------------

    numerology_result = analyze_numerology(
        timestamp,
        symbol
    )

    # ---------------------------------
    # Final Recommendation
    # ---------------------------------

    result = calculate_confidence(

        technical_result,

        astrology_result,

        numerology_result

    )

    # ---------------------------------
    # Extra Information
    # ---------------------------------

    result["symbol"] = symbol

    result["price"] = float(
        entry_df["close"].iloc[-1]
    )

    result["time"] = str(timestamp)

    return result
