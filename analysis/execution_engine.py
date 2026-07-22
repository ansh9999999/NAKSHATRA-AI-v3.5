"""
NAKSHATRA AI
Execution Engine
"""

from analysis.portfolio_engine import PortfolioEngine
from analysis.risk_manager import RiskManager
from analysis.research_engine import ResearchEngine


class ExecutionEngine:

    def __init__(self):

        self.portfolio = PortfolioEngine()

        self.risk = RiskManager()

        self.research = ResearchEngine()

    # -------------------------------------
    # Execute Signal
    # -------------------------------------

    def execute(
        self,
        signal
    ):

        confidence = signal["confidence"]

        entry = signal["price"]

        stop = signal["stop_loss"]

        target = signal["target"]

        rr = self.risk.risk_reward(
            entry,
            stop,
            target
        )

        valid, reason = self.risk.validate_trade(
            confidence,
            rr
        )

        if not valid:

            return {

                "status": "REJECTED",

                "reason": reason

            }

        qty = self.risk.calculate_quantity(
            entry,
            stop
        )

        allowed, reason = self.risk.can_open_trade(
            self.portfolio,
            entry,
            stop,
            qty
        )

        if not allowed:

            return {

                "status": "REJECTED",

                "reason": reason

            }

        opened = self.portfolio.open_position(

            symbol=signal["symbol"],

            signal=signal["signal"],

            entry=entry,

            stop_loss=stop,

            target=target,

            quantity=qty,

            confidence=confidence,

            grade=signal["grade"]

        )

        if not opened:

            return {

                "status": "FAILED",

                "reason": "Capital Not Available"

            }

        self.research.add_trade(signal)

        self.research.save()

        return {

            "status": "EXECUTED",

            "quantity": qty,

            "risk_reward": rr

      }
