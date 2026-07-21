"""
NAKSHATRA AI
Advanced Backtest Engine V2
"""

import pandas as pd


class BacktestEngine:

    def __init__(self):
        self.trades = []

    def add_trade(
        self,
        symbol,
        signal,
        entry,
        stop_loss,
        target,
        exit_price,
        score,
        reasons,
        grade="N/A",
        confidence=0,
        timeframe="MULTI",
        holding_candles=0
    ):

        pnl = 0
        result = "OPEN"

        # -------------------------
        # Calculate PnL
        # -------------------------

        if signal in ["BUY", "STRONG BUY"]:
            pnl = exit_price - entry

        elif signal in ["SELL", "STRONG SELL"]:
            pnl = entry - exit_price

        if pnl > 0:
            result = "WIN"

        elif pnl < 0:
            result = "LOSS"

        # -------------------------
        # Risk Reward
        # -------------------------

        risk = abs(entry - stop_loss)
        reward = abs(target - entry)

        risk_reward = 0

        if risk != 0:
            risk_reward = round(reward / risk, 2)

        # -------------------------
        # Store Trade
        # -------------------------

        trade = {

            "symbol": symbol,

            "signal": signal,

            "grade": grade,

            "confidence": confidence,

            "timeframe": timeframe,

            "entry": round(entry, 2),

            "stop_loss": round(stop_loss, 2),

            "target": round(target, 2),

            "exit": round(exit_price, 2),

            "score": score,

            "holding_candles": holding_candles,

            "risk_reward": risk_reward,

            "pnl": round(pnl, 2),

            "result": result,

            "reasons": ", ".join(reasons)

        }

        self.trades.append(trade)

    def dataframe(self):
        return pd.DataFrame(self.trades)

    def summary(self):

        df = self.dataframe()

        if df.empty:
            return {
                "Trades": 0,
                "Wins": 0,
                "Losses": 0,
                "Win Rate": 0,
                "Net PnL": 0,
                "Average RR": 0,
                "Average Confidence": 0
            }

        wins = len(df[df["result"] == "WIN"])
        losses = len(df[df["result"] == "LOSS"])

        total = len(df)

        pnl = df["pnl"].sum()

        avg_rr = round(df["risk_reward"].mean(), 2)

        avg_conf = round(df["confidence"].mean(), 2)

        return {

            "Trades": total,

            "Wins": wins,

            "Losses": losses,

            "Win Rate": round((wins / total) * 100, 2),

            "Net PnL": round(pnl, 2),

            "Average RR": avg_rr,

            "Average Confidence": avg_conf

        }

    def save_csv(self, filename="backtest_results.csv"):

        self.dataframe().to_csv(
            filename,
            index=False
        )

        return filename
