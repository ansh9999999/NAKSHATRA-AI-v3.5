"""
NAKSHATRA AI
Portfolio Engine
"""

import pandas as pd


class PortfolioEngine:

    def __init__(self, initial_capital=100000):

        self.initial_capital = initial_capital
        self.available_capital = initial_capital

        self.positions = []
        self.history = []

    # ---------------------------------------
    # Open Position
    # ---------------------------------------

    def open_position(
        self,
        symbol,
        signal,
        entry,
        stop_loss,
        target,
        quantity,
        confidence,
        grade
    ):

        investment = entry * quantity

        if investment > self.available_capital:
            return False

        self.available_capital -= investment

        self.positions.append({

            "symbol": symbol,

            "signal": signal,

            "entry": entry,

            "stop_loss": stop_loss,

            "target": target,

            "quantity": quantity,

            "confidence": confidence,

            "grade": grade,

            "investment": investment

        })

        return True

    # ---------------------------------------
    # Close Position
    # ---------------------------------------

    def close_position(
        self,
        symbol,
        exit_price
    ):

        for position in self.positions:

            if position["symbol"] == symbol:

                investment = position["investment"]

                qty = position["quantity"]

                entry = position["entry"]

                signal = position["signal"]

                if signal in ["BUY", "STRONG BUY"]:

                    pnl = (exit_price - entry) * qty

                else:

                    pnl = (entry - exit_price) * qty

                self.available_capital += investment + pnl

                trade = position.copy()

                trade["exit"] = exit_price

                trade["pnl"] = round(pnl, 2)

                trade["result"] = (
                    "WIN"
                    if pnl > 0
                    else "LOSS"
                )

                self.history.append(trade)

                self.positions.remove(position)

                return trade

        return None

    # ---------------------------------------
    # Portfolio Summary
    # ---------------------------------------

    def summary(self):

        history = pd.DataFrame(self.history)

        if history.empty:

            return {

                "capital": self.available_capital,

                "open_positions": len(self.positions),

                "closed_positions": 0,

                "net_profit": 0

            }

        return {

            "initial_capital":
                self.initial_capital,

            "available_capital":
                round(self.available_capital, 2),

            "open_positions":
                len(self.positions),

            "closed_positions":
                len(history),

            "net_profit":
                round(history["pnl"].sum(), 2),

            "wins":
                len(history[
                    history["result"] == "WIN"
                ]),

            "losses":
                len(history[
                    history["result"] == "LOSS"
                ])

        }

    # ---------------------------------------
    # Portfolio History
    # ---------------------------------------

    def dataframe(self):

        return pd.DataFrame(self.history)

    # ---------------------------------------
    # Asset Report
    # ---------------------------------------

    def asset_report(self):

        history = self.dataframe()

        if history.empty:

            return pd.DataFrame()

        return history.groupby("symbol")["pnl"].agg(

            Trades="count",

            NetProfit="sum",

            AveragePnL="mean"

        )

    # ---------------------------------------
    # Export
    # ---------------------------------------

    def export_csv(
        self,
        filename="portfolio_history.csv"
    ):

        self.dataframe().to_csv(
            filename,
            index=False
        )

        return filename
