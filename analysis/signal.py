"""
NAKSHATRA AI
Master Signal Engine v4.0
"""

from analysis.trend_engine import analyze_multi_timeframe
from analysis.momentum_engine import analyze_momentum
from analysis.smart_money_engine import analyze_smart_money
from analysis.confidence_engine import calculate_decision

from analysis.astrology_engine import analyze_astrology
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

    trend_data = {
        "5m": data["5m"],
        "15m": data["15m"],
        "1h": data["1h"],
        "1d": data["1d"]
    }

    trend_result = analyze_multi_timeframe(trend_data)

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

    # Delta candle timestamps are Unix integers. Convert them to a real
    # Python datetime before astrology/numerology modules use .day, .month, etc.
    if isinstance(timestamp, (int, float)):
        import datetime as _dt
        timestamp = _dt.datetime.fromtimestamp(float(timestamp), tz=_dt.timezone.utc)
    elif hasattr(timestamp, "to_pydatetime"):
        timestamp = timestamp.to_pydatetime()

    symbol = data.get("symbol", "BTCUSD")

    # ---------------------------------
    # Astrology
    # ---------------------------------

    astrology_result = analyze_astrology(timestamp)

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

    result = calculate_decision(

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
