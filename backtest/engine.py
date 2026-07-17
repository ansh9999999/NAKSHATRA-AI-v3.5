import pandas as pd


class BacktestEngine:

    def __init__(self):
        self.trades = []

    def add_trade(
        self,
        symbol,
        signal,
        entry,
        exit_price,
        score,
        reasons
    ):

        if signal == "BUY":
            pnl = exit_price - entry

        elif signal == "SELL":
            pnl = entry - exit_price

        else:
            return

        trade = {
            "symbol": symbol,
            "signal": signal,
            "entry": round(entry, 2),
            "exit": round(exit_price, 2),
            "pnl": round(pnl, 2),
            "score": score,
            "result": "WIN" if pnl > 0 else "LOSS",
            "reasons": reasons
        }

        self.trades.append(trade)

    def dataframe(self):
        return pd.DataFrame(self.trades)

    def summary(self):

        df = self.dataframe()

        if df.empty:
            return {
                "Trades": 0,
                "Win Rate": 0,
                "Net PnL": 0
            }

        wins = len(df[df["result"] == "WIN"])

        total = len(df)

        return {
            "Trades": total,
            "Wins": wins,
            "Losses": total - wins,
            "Win Rate": round((wins / total) * 100, 2),
            "Net PnL": round(df["pnl"].sum(), 2)
        }
