"""
NAKSHATRA AI
Learning Engine V2
Part 1
"""

import pandas as pd


class LearningEngine:

    def __init__(self, research_file="research_database.csv"):

        self.research_file = research_file

        try:
            self.df = pd.read_csv(research_file)
        except Exception:
            self.df = pd.DataFrame()

    # -------------------------------------
    # Recent Data Preference
    # -------------------------------------

    def _recent_data(self, recent=200):

        if self.df.empty:
            return self.df

        if len(self.df) <= recent:
            return self.df.copy()

        return self.df.tail(recent).copy()

    # -------------------------------------
    # Win Rate
    # -------------------------------------

    def _win_rate(self, data):

        if len(data) == 0:
            return 0

        wins = len(data[data["result"] == "WIN"])

        return round((wins / len(data)) * 100, 2)

    # -------------------------------------
    # Expectancy
    # -------------------------------------

    def _expectancy(self, data):

        if len(data) == 0:
            return 0

        return round(data["pnl"].mean(), 2)

    # -------------------------------------
    # Net Profit
    # -------------------------------------

    def _net_profit(self, data):

        if len(data) == 0:
            return 0

        return round(data["pnl"].sum(), 2)

    # -------------------------------------
    # Adaptive Score
    # -------------------------------------

    def _adaptive_score(self, win_rate, expectancy):

        score = 0

        # Win Rate

        if win_rate >= 80:
            score += 50

        elif win_rate >= 70:
            score += 40

        elif win_rate >= 60:
            score += 30

        elif win_rate >= 50:
            score += 15

        else:
            score -= 10

        # Expectancy

        if expectancy > 0:
            score += 20

        elif expectancy < 0:
            score -= 20

    return score
    # -------------------------------------
    # Generic Learning Model
    # -------------------------------------

    def _calculate_weight(self, column, recent=200):

        data = self._recent_data(recent)

        if data.empty:
            return {}

        weights = {}

        grouped = data.groupby(column)

        for value, group in grouped:

            trades = len(group)

            if trades < 5:
                continue

            win_rate = self._win_rate(group)
            expectancy = self._expectancy(group)
            net_profit = self._net_profit(group)

            score = self._adaptive_score(
                win_rate,
                expectancy
            )

            weights[value] = {

                "trades": trades,

                "win_rate": win_rate,

                "expectancy": expectancy,

                "net_profit": net_profit,

                "adaptive_score": score

            }

        return weights

    # -------------------------------------
    # Moon Learning
    # -------------------------------------

    def moon_weights(self):

        return self._calculate_weight("moon_phase")

    # -------------------------------------
    # Nakshatra Learning
    # -------------------------------------

    def nakshatra_weights(self):

        return self._calculate_weight("nakshatra")

    # -------------------------------------
    # Tithi Learning
    # -------------------------------------

    def tithi_weights(self):

        return self._calculate_weight("tithi")

    # -------------------------------------
    # Universal Day Learning
    # -------------------------------------

    def universal_day_weights(self):

        return self._calculate_weight("universal_day")

    # -------------------------------------
    # Symbol Learning
    # -------------------------------------

    def symbol_weights(self):

    return self._calculate_weight("symbol")
    # -------------------------------------
    # Confidence Band Learning
    # -------------------------------------

    def confidence_report(self):

        if self.df.empty:
            return {}

        bands = {
            "50-60": self.df[(self.df["confidence"] >= 50) & (self.df["confidence"] < 60)],
            "60-70": self.df[(self.df["confidence"] >= 60) & (self.df["confidence"] < 70)],
            "70-80": self.df[(self.df["confidence"] >= 70) & (self.df["confidence"] < 80)],
            "80-90": self.df[(self.df["confidence"] >= 80) & (self.df["confidence"] < 90)],
            "90-100": self.df[(self.df["confidence"] >= 90)],
        }

        report = {}

        for name, data in bands.items():

            if len(data) < 5:
                continue

            report[name] = {
                "trades": len(data),
                "win_rate": self._win_rate(data),
                "expectancy": self._expectancy(data),
                "net_profit": self._net_profit(data)
            }

        return report

    # -------------------------------------
    # Summary
    # -------------------------------------

    def summary(self):

        if self.df.empty:

            return {
                "records": 0,
                "status": "No Research Data"
            }

        return {

            "records": len(self.df),

            "moon_models": len(self.moon_weights()),

            "nakshatra_models": len(self.nakshatra_weights()),

            "tithi_models": len(self.tithi_weights()),

            "numerology_models": len(self.universal_day_weights()),

            "symbol_models": len(self.symbol_weights()),

            "confidence_models": len(self.confidence_report())

        }

    # -------------------------------------
    # Best Model
    # -------------------------------------

    def best_model(self, weights):

        if not weights:
            return None

        return max(
            weights.items(),
            key=lambda x: x[1]["adaptive_score"]
        )

    def best_moon(self):
        return self.best_model(self.moon_weights())

    def best_nakshatra(self):
        return self.best_model(self.nakshatra_weights())

    def best_tithi(self):
        return self.best_model(self.tithi_weights())

    def best_day(self):
        return self.best_model(self.universal_day_weights())
