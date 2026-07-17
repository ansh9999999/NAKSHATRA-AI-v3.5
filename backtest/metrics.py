"""
NAKSHATRA AI
Backtest Performance Metrics
"""

import pandas as pd


def calculate_metrics(df):
    """
    Calculate backtest performance metrics.

    Parameters
    ----------
    df : pandas.DataFrame

    Required Columns
    ----------------
    pnl
    result

    Returns
    -------
    dict
    """

    if df.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "net_profit": 0,
            "gross_profit": 0,
            "gross_loss": 0,
            "profit_factor": 0,
            "average_win": 0,
            "average_loss": 0,
            "expectancy": 0,
            "max_drawdown": 0
        }

    wins = df[df["result"] == "WIN"]
    losses = df[df["result"] == "LOSS"]

    total = len(df)

    total_wins = len(wins)
    total_losses = len(losses)

    gross_profit = wins["pnl"].sum()

    gross_loss = abs(losses["pnl"].sum())

    net_profit = df["pnl"].sum()

    win_rate = (total_wins / total) * 100 if total else 0

    average_win = wins["pnl"].mean() if total_wins else 0

    average_loss = losses["pnl"].mean() if total_losses else 0

    if gross_loss == 0:
        profit_factor = 999
    else:
        profit_factor = gross_profit / gross_loss

    expectancy = (
        (win_rate / 100) * average_win
        +
        ((100 - win_rate) / 100) * average_loss
    )

    equity = df["pnl"].cumsum()

    running_max = equity.cummax()

    drawdown = running_max - equity

    max_drawdown = drawdown.max()

    return {

        "trades": total,

        "wins": total_wins,

        "losses": total_losses,

        "win_rate": round(win_rate, 2),

        "net_profit": round(net_profit, 2),

        "gross_profit": round(gross_profit, 2),

        "gross_loss": round(gross_loss, 2),

        "profit_factor": round(profit_factor, 2),

        "average_win": round(average_win, 2),

        "average_loss": round(average_loss, 2),

        "expectancy": round(expectancy, 2),

        "max_drawdown": round(max_drawdown, 2)

  }
