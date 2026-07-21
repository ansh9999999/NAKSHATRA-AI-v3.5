from analysis.trend_engine import analyze_multi_timeframe
from analysis.momentum_engine import analyze_momentum
from analysis.smart_money_engine import analyze_smart_money
from analysis.confidence_engine import calculate_confidence


def generate_signal(data):
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

    # -----------------------------
    # Trend Analysis (All Timeframes)
    # -----------------------------
    trend_result = analyze_multi_timeframe(data)

    # -----------------------------
    # Entry Timeframe
    # -----------------------------
    entry_df = data["5m"]

    if entry_df.empty:
        return {
            "signal": "WAIT",
            "confidence": 0,
            "score": 0,
            "reasons": ["No Entry Data"]
        }

    # -----------------------------
    # Momentum
    # -----------------------------
    momentum_result = analyze_momentum(entry_df)

    # -----------------------------
    # Smart Money
    # -----------------------------
    smart_money_result = analyze_smart_money(entry_df)

    # -----------------------------
    # Final Confidence
    # -----------------------------
    final_result = calculate_confidence(
        trend_result,
        momentum_result,
        smart_money_result
    )

    price = float(entry_df["close"].iloc[-1])

    final_result["price"] = round(price, 2)

    final_result["trend"] = trend_result

    final_result["momentum"] = momentum_result

    final_result["smart_money"] = smart_money_result

    return final_result
