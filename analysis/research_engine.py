"""
NAKSHATRA AI
Research Engine
"""

import os
import pandas as pd


class ResearchEngine:

    def __init__(self, filename="research_database.csv"):

        self.filename = filename

        if os.path.exists(filename):

            self.df = pd.read_csv(filename)

        else:

            self.df = pd.DataFrame(columns=[

                "date",
                "symbol",

                "signal",
                "grade",
                "confidence",
                "score",

                "price",

                "moon_phase",
                "nakshatra",
                "tithi",
                "rahu_active",

                "universal_day",
                "symbol_number",

                "result",
                "pnl"

            ])

    def add_trade(self, signal_result, trade_result=None):

        lunar = signal_result.get("lunar", {})
        numerology = signal_result.get("numerology", {})

        row = {

            "date":
                signal_result.get("timestamp"),

            "symbol":
                signal_result.get("symbol", "BTCUSD"),

            "signal":
                signal_result.get("signal"),

            "grade":
                signal_result.get("grade"),

            "confidence":
                signal_result.get("confidence"),

            "score":
                signal_result.get("score"),

            "price":
                signal_result.get("price"),

            "moon_phase":
                lunar.get("moon", {}).get("phase"),

            "nakshatra":
                lunar.get("nakshatra", {}).get("name"),

            "tithi":
                lunar.get("tithi", {}).get("name"),

            "rahu_active":
                lunar.get("rahu", {}).get("active"),

            "universal_day":
                numerology.get("universal_day"),

            "symbol_number":
                numerology.get("symbol_number"),

            "result":
                "",

            "pnl":
                0

        }

        if trade_result is not None:

            row["result"] = trade_result.get("result")

            row["pnl"] = trade_result.get("pnl", 0)

        self.df.loc[len(self.df)] = row

    def save(self):

        self.df.to_csv(
            self.filename,
            index=False
        )

    def summary(self):

        if self.df.empty:

            return {

                "records": 0

            }

        return {

            "records": len(self.df),

            "wins": len(
                self.df[self.df["result"] == "WIN"]
            ),

            "losses": len(
                self.df[self.df["result"] == "LOSS"]
            ),

            "net_pnl": round(
                self.df["pnl"].sum(),
                2
            )

        }

    def moon_statistics(self):

        if self.df.empty:

            return pd.DataFrame()

        return self.df.groupby(
            "moon_phase"
        )["pnl"].agg(

            Trades="count",

            NetProfit="sum",

            AveragePnL="mean"

        )

    def nakshatra_statistics(self):

        if self.df.empty:

            return pd.DataFrame()

        return self.df.groupby(
            "nakshatra"
        )["pnl"].agg(

            Trades="count",

            NetProfit="sum",

            AveragePnL="mean"

        )

    def numerology_statistics(self):

        if self.df.empty:

            return pd.DataFrame()

        return self.df.groupby(
            "universal_day"
        )["pnl"].agg(

            Trades="count",

            NetProfit="sum",

            AveragePnL="mean"

        )

    def export_excel(self,
                     filename="research_report.xlsx"):

        self.df.to_excel(
            filename,
            index=False
        )

        return filename
