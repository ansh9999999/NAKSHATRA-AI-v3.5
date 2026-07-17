"""
NAKSHATRA AI
Take Profit Engine
"""


def calculate_take_profit(
    signal,
    entry_price,
    stop_loss,
    risk_reward=2.0
):
    """
    Calculate Take Profit using Risk Reward Ratio.

    Parameters
    ----------
    signal : BUY / SELL
    entry_price : float
    stop_loss : float
    risk_reward : float

    Returns
    -------
    dict
    """

    signal = signal.upper()

    risk = abs(entry_price - stop_loss)

    if signal in ["BUY", "STRONG BUY"]:

        target = entry_price + (risk * risk_reward)

    elif signal in ["SELL", "STRONG SELL"]:

        target = entry_price - (risk * risk_reward)

    else:

        target = entry_price

    return {

        "target": round(target, 2),

        "risk": round(risk, 2),

        "reward": round(risk * risk_reward, 2),

        "risk_reward": risk_reward

    }


def partial_targets(
    signal,
    entry_price,
    stop_loss
):
    """
    Generate TP1 TP2 TP3
    """

    signal = signal.upper()

    risk = abs(entry_price - stop_loss)

    if signal in ["BUY", "STRONG BUY"]:

        tp1 = entry_price + risk
        tp2 = entry_price + (risk * 2)
        tp3 = entry_price + (risk * 3)

    elif signal in ["SELL", "STRONG SELL"]:

        tp1 = entry_price - risk
        tp2 = entry_price - (risk * 2)
        tp3 = entry_price - (risk * 3)

    else:

        tp1 = tp2 = tp3 = entry_price

    return {

        "TP1": round(tp1, 2),

        "TP2": round(tp2, 2),

        "TP3": round(tp3, 2)

    }
