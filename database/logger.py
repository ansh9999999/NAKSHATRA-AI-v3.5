"""
NAKSHATRA AI
Trade Logger
"""

from datetime import datetime

from database.models import save_trade


def log_trade(symbol, signal_data, trade):

    trade_record = {

        "trade_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        "symbol": symbol,

        "signal": trade["signal"],

        "entry": trade["entry"],

        "stop_loss": trade["stop_loss"],

        "target": trade["target"],

        "exit_price": 0,

        "pnl": 0,

        "score": signal_data["score"],

        "trend": signal_data["trend"],

        "volume": signal_data["volume_status"],

        "liquidity": signal_data["liquidity"],

        "result": "OPEN"

    }

    save_trade(trade_record)
