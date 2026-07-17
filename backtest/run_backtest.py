"""
NAKSHATRA AI
Run Historical Backtest
"""

from history import get_history

from analysis.signal import generate_signal

from risk.trade_manager import create_trade

from backtest.engine import BacktestEngine

from backtest.report import print_report


def run_backtest(symbol="BTCUSD"):

    df = get_history(
        symbol=symbol,
        resolution="5m",
        limit=500
    )

    engine = BacktestEngine()

    for i in range(60, len(df)-1):

        data = df.iloc[:i].copy()

        signal = generate_signal(data)

        if signal["signal"] == "WAIT":
            continue

        trade = create_trade(

            signal=signal["signal"],

            entry_price=signal["price"],

            atr=signal["atr"]

        )

        if trade is None:
            continue

        exit_price = float(df.iloc[i+1]["close"])

        engine.add_trade(

            symbol=symbol,

            signal=trade["signal"],

            entry=trade["entry"],

            stop_loss=trade["stop_loss"],

            target=trade["target"],

            exit_price=exit_price,

            score=signal["score"],

            reasons=signal["reasons"]

        )

    engine.save_csv()

    print_report(engine.dataframe())


if __name__ == "__main__":

    run_backtest()
