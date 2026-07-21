"""
NAKSHATRA AI
Strategy Optimizer
"""

import pandas as pd


class StrategyOptimizer:

    def __init__(self, research_file="research_database.csv"):

        try:
            self.df = pd.read_csv(research_file)
        except Exception:
            self.df = pd.DataFrame()

    def _performance(self, df):

        if df.empty:
            return None

        trades = len(df)

        wins = len(df[df["result"] == "WIN"])

        losses = len(df[df["result"] == "LOSS"])

        pnl = round(df["pnl"].sum(), 2)

        avg_pnl = round(df["pnl"].mean(), 2)

        win_rate = round((wins / trades) * 100, 2)

        return {

            "trades": trades,

            "wins": wins,

            "losses": losses,

            "win_rate": win_rate,

            "net_pnl": pnl,

            "average_pnl": avg_pnl

        }

    # ------------------------------------
    # Grade Analysis
    # ------------------------------------

    def grade_report(self):

        report = {}

        if self.df.empty:
            return report

        for grade in sorted(self.df["grade"].dropna().unique()):

            report[grade] = self._performance(

                self.df[self.df["grade"] == grade]

            )

        return report

    # ------------------------------------
    # Moon Phase Analysis
    # ------------------------------------

    def moon_report(self):

        report = {}

        if self.df.empty:
            return report

        for phase in sorted(self.df["moon_phase"].dropna().unique()):

            report[phase] = self._performance(

                self.df[self.df["moon_phase"] == phase]

            )

        return report

    # ------------------------------------
    # Nakshatra Analysis
    # ------------------------------------

    def nakshatra_report(self):

        report = {}

        if self.df.empty:
            return report

        for name in sorted(self.df["nakshatra"].dropna().unique()):

            report[name] = self._performance(

                self.df[self.df["nakshatra"] == name]

            )

        return report

    # ------------------------------------
    # Tithi Analysis
    # ------------------------------------

    def tithi_report(self):

        report = {}

        if self.df.empty:
            return report

        for name in sorted(self.df["tithi"].dropna().unique()):

            report[name] = self._performance(

                self.df[self.df["tithi"] == name]

            )

        return report

    # ------------------------------------
    # Universal Day Analysis
    # ------------------------------------

    def numerology_report(self):

        report = {}

        if self.df.empty:
            return report

        for day in sorted(self.df["universal_day"].dropna().unique()):

            report[int(day)] = self._performance(

                self.df[self.df["universal_day"] == day]

            )

        return report

    # ------------------------------------
    # Symbol Analysis
    # ------------------------------------

    def symbol_report(self):

        report = {}

        if self.df.empty:
            return report

        for symbol in sorted(self.df["symbol"].dropna().unique()):

            report[symbol] = self._performance(

                self.df[self.df["symbol"] == symbol]

            )

        return report

    # ------------------------------------
    # Best Configurations
    # ------------------------------------

    def best_nakshatra(self):

        report = self.nakshatra_report()

        if not report:
            return None

        return max(
            report.items(),
            key=lambda x: x[1]["win_rate"]
        )

    def best_moon_phase(self):

        report = self.moon_report()

        if not report:
            return None

        return max(
            report.items(),
            key=lambda x: x[1]["win_rate"]
        )

    def best_universal_day(self):

        report = self.numerology_report()

        if not report:
            return None

        return max(
            report.items(),
            key=lambda x: x[1]["win_rate"]
        )

    # ------------------------------------
    # Overall Summary
    # ------------------------------------

    def summary(self):

        if self.df.empty:

            return {

                "status": "No research data"

            }

        return {

            "records": len(self.df),

            "best_nakshatra": self.best_nakshatra(),

            "best_moon_phase": self.best_moon_phase(),

            "best_universal_day": self.best_universal_day()

  }
