"""
NAKSHATRA AI
Trade Manager
"""

from risk.stop_loss import calculate_stop_loss
from risk.take_profit import calculate_take_profit, partial_targets
from risk.position_size import calculate_position_size
from risk.risk_reward import calculate_risk_reward, validate_trade


def create_trade(
    signal,
    entry_price,
    atr,
    capital=100000,
    risk_percent=1.0,
    atr_multiplier=2.0,
    rr=2.0
):
    """
    Create complete trade plan.
    """

    signal = signal.upper()

    if signal not in ["BUY", "SELL", "STRONG BUY", "STRONG SELL"]:
        return None

    sl = calculate_stop_loss(
        signal,
        entry_price,
        atr,
        atr_multiplier
    )

    tp = calculate_take_profit(
        signal,
        entry_price,
        sl["stop_loss"],
        rr
    )

    targets = partial_targets(
        signal,
        entry_price,
        sl["stop_loss"]
    )

    qty = calculate_position_size(
        capital,
        risk_percent,
        entry_price,
        sl["stop_loss"]
    )

    rr_info = calculate_risk_reward(
        entry_price,
        sl["stop_loss"],
        tp["target"]
    )

    trade = {
        "signal": signal,
        "entry": round(entry_price, 2),
        "stop_loss": sl["stop_loss"],
        "target": tp["target"],
        "tp1": targets["TP1"],
        "tp2": targets["TP2"],
        "tp3": targets["TP3"],
        "quantity": qty,
        "risk_reward": rr_info["ratio"],
        "trade_ok": validate_trade(
            rr_info["ratio"]
        )["valid"]
    }

    return trade
