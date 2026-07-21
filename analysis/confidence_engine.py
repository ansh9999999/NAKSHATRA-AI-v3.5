# analysis/confidence_engine.py

def calculate_confidence(
    trend_result,
    momentum_result,
    smart_money_result
):
    """
    Combine all engines into one final confidence score.

    Returns:
    {
        confidence,
        grade,
        signal,
        score,
        reasons
    }
    """

    score = (
        trend_result["total_score"]
        + momentum_result["score"]
        + smart_money_result["score"]
    )

    confidence = min(abs(score), 100)

    reasons = []
    reasons.extend(trend_result["reasons"])
    reasons.extend(momentum_result["reasons"])
    reasons.extend(smart_money_result["reasons"])

    # -------------------------
    # Grade
    # -------------------------

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

    # -------------------------
    # Final Signal
    # -------------------------

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
        "score": score,
        "confidence": confidence,
        "grade": grade,
        "signal": signal,
        "reasons": reasons,
    }
