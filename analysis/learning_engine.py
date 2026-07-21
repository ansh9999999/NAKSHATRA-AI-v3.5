"""
NAKSHATRA AI
Learning Engine
"""

import pandas as pd


class LearningEngine:

    def __init__(self, research_file="research_database.csv"):

        self.research_file = research_file

        try:
            self.df = pd.read_csv(research_file)
        except:
            self.df = pd.DataFrame()

    def _calculate_weight(self, column):

        if self.df.empty:
            return {}

        weights = {}

        grouped = self.df.groupby(column)

        for value, data in grouped:

            total = len(data)

            if total < 5:
                continue

            wins = len(data[data["result"] == "WIN"])

            weight = round((wins / total) * 100, 2)

            weights[value] = weight

        return weights

    def moon_weights(self):

        return self._calculate_weight("moon_phase")

    def nakshatra_weights(self):

        return self._calculate_weight("nakshatra")

    def tithi_weights(self):

        return self._calculate_weight("tithi")

    def universal_day_weights(self):

        return self._calculate_weight("universal_day")

    def symbol_weights(self):

        return self._calculate_weight("symbol")

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

            "numerology_models": len(self.universal_day_weights())

        }
