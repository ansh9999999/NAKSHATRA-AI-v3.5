"""
NAKSHATRA AI
Adaptive Confidence Engine
"""

from analysis.learning_engine import LearningEngine


class AdaptiveConfidence:

    def __init__(self):

        self.learning = LearningEngine()

        self.moon_weights = self.learning.moon_weights()

        self.nakshatra_weights = self.learning.nakshatra_weights()

        self.tithi_weights = self.learning.tithi_weights()

        self.day_weights = self.learning.universal_day_weights()

    def _adjust(self, value, weights):

        if value not in weights:
            return 0

        win_rate = weights[value]

        # ----------------------------------
        # Adaptive Score
        # ----------------------------------

        if win_rate >= 80:
            return 10

        elif win_rate >= 70:
            return 7

        elif win_rate >= 60:
            return 5

        elif win_rate >= 50:
            return 2

        elif win_rate >= 40:
            return -3

        else:
            return -8

    def calculate(
        self,
        confidence,
        lunar_result,
        numerology_result
    ):

        score = 0

        # -------------------------
        # Moon Phase
        # -------------------------

        moon = lunar_result.get(
            "moon",
            {}
        ).get(
            "phase"
        )

        score += self._adjust(
            moon,
            self.moon_weights
        )

        # -------------------------
        # Nakshatra
        # -------------------------

        nakshatra = lunar_result.get(
            "nakshatra",
            {}
        ).get(
            "name"
        )

        score += self._adjust(
            nakshatra,
            self.nakshatra_weights
        )

        # -------------------------
        # Tithi
        # -------------------------

        tithi = lunar_result.get(
            "tithi",
            {}
        ).get(
            "name"
        )

        score += self._adjust(
            tithi,
            self.tithi_weights
        )

        # -------------------------
        # Universal Day
        # -------------------------

        day = numerology_result.get(
            "universal_day"
        )

        score += self._adjust(
            day,
            self.day_weights
        )

        adaptive_confidence = confidence + score

        adaptive_confidence = max(
            0,
            min(100, adaptive_confidence)
        )

        return {

            "confidence": adaptive_confidence,

            "adaptive_score": score,

            "moon_weight":
                self.moon_weights.get(moon, 0),

            "nakshatra_weight":
                self.nakshatra_weights.get(
                    nakshatra,
                    0
                ),

            "tithi_weight":
                self.tithi_weights.get(
                    tithi,
                    0
                ),

            "day_weight":
                self.day_weights.get(
                    day,
                    0
                )

        }
