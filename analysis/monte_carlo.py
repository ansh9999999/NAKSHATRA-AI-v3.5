"""
NAKSHATRA AI
Monte Carlo Simulation Engine
"""

import random
import pandas as pd


class MonteCarloEngine:

    def __init__(self, dataframe):

        self.df = dataframe.copy()

    # -----------------------------------
    # Single Simulation
    # -----------------------------------

    def simulate_once(self):

        if self.df.empty:

            return {

                "ending_balance": 0,

                "net_profit": 0,

                "max_drawdown": 0

            }

        pnl_list = list(self.df["pnl"])

        random.shuffle(pnl_list)

        balance = 100000

        peak = balance

        max_dd = 0

        for pnl in pnl_list:

            balance += pnl

            if balance > peak:

                peak = balance

            drawdown = peak - balance

            if drawdown > max_dd:

                max_dd = drawdown

        return {

            "ending_balance": round(balance, 2),

            "net_profit": round(balance - 100000, 2),

            "max_drawdown": round(max_dd, 2)

        }

    # -----------------------------------
    # Multiple Simulations
    # -----------------------------------

    def run(self, simulations=1000):

        results = []

        for _ in range(simulations):

            results.append(

                self.simulate_once()

            )

        return pd.DataFrame(results)

    # -----------------------------------
    # Summary
    # -----------------------------------

    def summary(self, simulations=1000):

        df = self.run(simulations)

        return {

            "simulations": simulations,

            "average_profit":
                round(df["net_profit"].mean(), 2),

            "best_profit":
                round(df["net_profit"].max(), 2),

            "worst_profit":
                round(df["net_profit"].min(), 2),

            "average_drawdown":
                round(df["max_drawdown"].mean(), 2),

            "maximum_drawdown":
                round(df["max_drawdown"].max(), 2),

            "minimum_drawdown":
                round(df["max_drawdown"].min(), 2)

        }

    # -----------------------------------
    # Risk of Ruin
    # -----------------------------------

    def risk_of_ruin(
        self,
        simulations=1000,
        ruin_level=50000
    ):

        df = self.run(simulations)

        ruined = len(

            df[
                df["ending_balance"] <= ruin_level
            ]

        )

        probability = round(

            (ruined / simulations) * 100,

            2

        )

        return {

            "ruined_runs": ruined,

            "simulations": simulations,

            "risk_of_ruin_percent": probability

        }

    # -----------------------------------
    # Losing Streak
    # -----------------------------------

    def longest_losing_streak(self):

        if self.df.empty:

            return 0

        streak = 0

        maximum = 0

        for pnl in self.df["pnl"]:

            if pnl < 0:

                streak += 1

                maximum = max(

                    maximum,

                    streak

                )

            else:

                streak = 0

        return maximum
