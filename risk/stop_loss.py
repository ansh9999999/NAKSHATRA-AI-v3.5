"""
NAKSHATRA AI
ATR Based Stop Loss Engine
"""


def calculate_stop_loss(
    signal,
    entry_price,
    atr,
    multiplier=2.0
):
    """
    Calculate ATR based Stop Loss.

    Parameters
    ----------
    signal : str
        BUY / STRONG BUY / SELL / STRONG SELL

    entry_price : float

    atr : float

    multiplier : float
        ATR Multiplier (Default = 2)

    Returns
    -------
    dict
    """

    if atr <= 0:
        return {
            "stop_loss": entry_price,
            "risk": 0,
            "multiplier": multiplier
        }

    signal = signal.upper()

    if signal in ["BUY", "STRONG BUY"]:

        stop_loss = entry_price - (atr * multiplier)

    elif signal in ["SELL", "STRONG SELL"]:

        stop_loss = entry_price + (atr * multiplier)

    else:

        stop_loss = entry_price

    risk = abs(entry_price - stop_loss)

    return {

        "stop_loss": round(stop_loss, 2),

        "risk": round(risk, 2),

        "multiplier": multiplier

    }


def trailing_stop(
    signal,
    current_price,
    current_stop,
    atr,
    multiplier=2.0
):
    """
    ATR Based Trailing Stop Loss.
    """

    signal = signal.upper()

    if signal in ["BUY", "STRONG BUY"]:

        new_stop = current_price - (atr * multiplier)

        if new_stop > current_stop:
            return round(new_stop, 2)

        return round(current_stop, 2)

    elif signal in ["SELL", "STRONG SELL"]:

        new_stop = current_price + (atr * multiplier)

        if new_stop < current_stop:
            return round(new_stop, 2)

        return round(current_stop, 2)

    return round(current_stop, 2)
