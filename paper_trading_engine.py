"""
NAKSHATRA AI
Paper Trading Engine
"""

from analysis.signal import generate_signal
from analysis.trade_planner import TradePlanner
from analysis.execution_engine import ExecutionEngine


class PaperTradingEngine:

    def __init__(self):

        self.planner = TradePlanner()

        self.execution = ExecutionEngine()

    def process_market(self, symbol, market_data):

        signal = generate_signal(market_data)

        if signal["signal"] == "WAIT":

            return {

                "status": "WAIT",

                "reason": "No Trade"

            }

        atr = signal["momentum"]["atr"]

        trade = self.planner.create_trade(

            signal["signal"],

            signal["price"],

            atr

        )

        if trade is None:

            return {

                "status": "WAIT"

            }

        signal["symbol"] = symbol

        signal["entry"] = trade["entry"]

        signal["stop_loss"] = trade["stop_loss"]

        signal["target"] = trade["target1"]

        signal["target1"] = trade["target1"]

        signal["target2"] = trade["target2"]

        signal["target3"] = trade["target3"]

        signal["risk_reward"] = trade["risk_reward"]

        result = self.execution.execute(signal)

        return {

            "symbol": symbol,

            "signal": signal,

            "execution": result

        }

    def portfolio(self):

        return self.execution.portfolio.summary()

    def research(self):

        return self.execution.research.summary()
