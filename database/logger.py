"""
NAKSHATRA AI
Database Trade Logger
"""

from datetime import datetime

from database.models import save_trade


def log_trade(symbol, signal_data, trade):
    """
    Save a newly generated trade to the database.
    """

    trade_record = {
        "trade_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "signal": trade.get("signal", signal_data.get("signal", "WAIT")),
        "entry": trade.get("entry", 0),
        "stop_loss": trade.get("stop_loss", 0),
        "target": trade.get("target", 0),
        "exit_price": 0,
        "pnl": 0,
        "score": signal_data.get("score", 0),
        "trend": signal_data.get("trend", "UNKNOWN"),
        "volume": signal_data.get("volume_status", "UNKNOWN"),
        "liquidity": signal_data.get("liquidity", "UNKNOWN"),
        "result": "OPEN",
    }

    save_trade(trade_record)

    return trade_record
