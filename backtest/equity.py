"""
NAKSHATRA AI
Equity Curve Engine
"""


class EquityCurve:

    def __init__(self, starting_capital=100000):

        self.starting_capital = starting_capital

        self.balance = starting_capital

        self.highest_balance = starting_capital

        self.max_drawdown = 0

        self.history = []

    def update(self, pnl):

        self.balance += pnl

        if self.balance > self.highest_balance:

            self.highest_balance = self.balance

        drawdown = self.highest_balance - self.balance

        if drawdown > self.max_drawdown:

            self.max_drawdown = drawdown

        self.history.append({

            "balance": round(self.balance, 2),

            "pnl": round(pnl, 2),

            "drawdown": round(drawdown, 2)

        })

    def summary(self):

        total_return = (

            (self.balance - self.starting_capital)

            / self.starting_capital

        ) * 100

        return {

            "starting_capital": round(self.starting_capital, 2),

            "ending_capital": round(self.balance, 2),

            "net_profit": round(
                self.balance - self.starting_capital,
                2
            ),

            "return_percent": round(total_return, 2),

            "max_drawdown": round(
                self.max_drawdown,
                2
            )

        }
