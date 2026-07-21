"""
NAKSHATRA AI
Master Signal Engine
"""

from analysis.trend_engine import analyze_multi_timeframe
from analysis.momentum_engine import analyze_momentum
from analysis.smart_money_engine import analyze_smart_money
from analysis.confidence_engine import calculate_confidence

from analysis.lunar_engine import analyze_lunar
from analysis.numerology_engine import analyze_numerology


def generate_signal(data):
    """
    data = {
        "5m": DataFrame,
        "15m": DataFrame,
        "1h": DataFrame,
        "1d": DataFrame,
        "1w": DataFrame,
        "1mo": DataFrame,

        # Optional
        "symbol": "BTCUSD"
    }
    """

    # ---------------------------------
    # Trend Analysis
    # ---------------------------------

    trend_result = analyze_multi_timeframe(data)

    # ---------------------------------
    # Entry Timeframe
    # ---------------------------------

    entry_df = data["5m"]

    if entry_df.empty:
        return {
            "signal": "WAIT",
            "confidence": 0,
            "score": 0,
            "grade": "REJECT",
            "reasons": ["No Entry Data"]
        }

    # ---------------------------------
    # Momentum
    # ---------------------------------

    momentum_result = analyze_momentum(entry_df)

    # ---------------------------------
    # Smart Money
    # ---------------------------------

    smart_money_result = analyze_smart_money(entry_df)

    # ---------------------------------
    # Time
    # ---------------------------------

    timestamp = entry_df.index[-1]

    if hasattr(timestamp, "to_pydatetime"):
        timestamp = timestamp.to_pydatetime()

    symbol = data.get("symbol", "BTCUSD")

    # ---------------------------------
    # Lunar Engine
    # ---------------------------------

    lunar_result = analyze_lunar(timestamp)

    # ---------------------------------
    # Numerology Engine
    # ---------------------------------

    numerology_result = analyze_numerology(
        timestamp,
        symbol
    )

    # ---------------------------------
    # Confidence Engine
    # ---------------------------------

    final_result = calculate_confidence(
        trend_result,
        momentum_result,
        smart_money_result
    )

    # ---------------------------------
    # Extra Scores
    # ---------------------------------

    final_result["score"] += lunar_result["score"]
    final_result["score"] += numerology_result["score"]

    confidence = (
        final_result["confidence"]
        + lunar_result["score"]
        + numerology_result["score"]
    )

    confidence = max(0, min(100, confidence))

    final_result["confidence"] = confidence

    # ---------------------------------
    # Grade
    # ---------------------------------

    if confidence >= 90:
        grade = "A+"

    elif confidence >= 80:
        grade = "A"

    elif confidence >= 70:
        grade = "B"

    elif confidence >= 60:
        grade = "C"

    else:
        grade = "REJECT"

    final_result["grade"] = grade

    # ---------------------------------
    # Price
    # ---------------------------------

    price = float(entry_df["close"].iloc[-1])

    final_result["price"] = round(price, 2)

    # ---------------------------------
    # Attach Results
    # ---------------------------------

    final_result["trend"] = trend_result

    final_result["momentum"] = momentum_result

    final_result["smart_money"] = smart_money_result

    final_result["lunar"] = lunar_result

    final_result["numerology"] = numerology_result

    # ---------------------------------
    # Reasons
    # ---------------------------------

    reasons = []

    reasons.extend(final_result.get("reasons", []))
    reasons.extend(lunar_result.get("reasons", []))
    reasons.extend(numerology_result.get("reasons", []))

    final_result["reasons"] = reasons

    return final_result
