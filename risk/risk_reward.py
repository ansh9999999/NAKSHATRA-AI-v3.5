"""
NAKSHATRA AI
Risk Reward Engine
"""


def calculate_risk_reward(
    entry_price,
    stop_loss,
    target_price
):
    """
    Calculate Risk Reward Ratio.
    """

    risk = abs(entry_price - stop_loss)

    reward = abs(target_price - entry_price)

    if risk == 0:

        ratio = 0

    else:

        ratio = reward / risk

    return {

        "risk": round(risk, 2),

        "reward": round(reward, 2),

        "ratio": round(ratio, 2)

    }


def validate_trade(
    ratio,
    minimum_ratio=2.0
):
    """
    Validate Trade Quality.
    """

    if ratio >= minimum_ratio:

        return {

            "valid": True,

            "message": "Good Trade"

        }

    return {

        "valid": False,

        "message": "Risk Reward Too Low"

    }
