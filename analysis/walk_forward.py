"""
NAKSHATRA AI
Walk Forward Testing Engine
"""

import pandas as pd


class WalkForwardEngine:

    def __init__(self, dataframe):

        self.df = dataframe.copy()

        if "timestamp" in self.df.columns:
            self.df["timestamp"] = pd.to_datetime(
                self.df["timestamp"]
            )

    # ---------------------------------------
    # Split Dataset
    # ---------------------------------------

    def split(
        self,
        train_ratio=0.60,
        validation_ratio=0.20
    ):

        total = len(self.df)

        train_end = int(total * train_ratio)

        validation_end = train_end + int(
            total * validation_ratio
        )

        train = self.df.iloc[:train_end]

        validation = self.df.iloc[
            train_end:validation_end
        ]

        test = self.df.iloc[
            validation_end:
        ]

        return train, validation, test

    # ---------------------------------------
    # Evaluate Dataset
    # ---------------------------------------

    def evaluate(self, data):

        if data.empty:

            return {

                "trades": 0,

                "wins": 0,

                "losses": 0,

                "win_rate": 0,

                "net_profit": 0,

                "average_pnl": 0

            }

        wins = len(
            data[data["result"] == "WIN"]
        )

        losses = len(
            data[data["result"] == "LOSS"]
        )

        trades = len(data)

        pnl = round(
            data["pnl"].sum(),
            2
        )

        avg = round(
            data["pnl"].mean(),
            2
        )

        win_rate = round(
            (wins / trades) * 100,
            2
        )

        return {

            "trades": trades,

            "wins": wins,

            "losses": losses,

            "win_rate": win_rate,

            "net_profit": pnl,

            "average_pnl": avg

        }

    # ---------------------------------------
    # Run Walk Forward
    # ---------------------------------------

    def run(
        self,
        train_ratio=0.60,
        validation_ratio=0.20
    ):

        train, validation, test = self.split(
            train_ratio,
            validation_ratio
        )

        return {

            "train": self.evaluate(train),

            "validation": self.evaluate(
                validation
            ),

            "test": self.evaluate(test)

        }

    # ---------------------------------------
    # Stability Score
    # ---------------------------------------

    def stability_score(self):

        result = self.run()

        train = result["train"]["win_rate"]

        validation = result["validation"]["win_rate"]

        test = result["test"]["win_rate"]

        spread = max(
            train,
            validation,
            test
        ) - min(
            train,
            validation,
            test
        )

        score = max(
            0,
            round(
                100 - spread,
                2
            )
        )

        return {

            "stability_score": score,

            "train": train,

            "validation": validation,

            "test": test

      }
