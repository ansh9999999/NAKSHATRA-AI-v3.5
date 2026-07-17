"""
NAKSHATRA AI
Advanced Historical Backtest
"""

from history import get_history
from analysis.signal import generate_signal
from risk.trade_manager import create_trade
from backtest.engine import BacktestEngine
from backtest.report import print_report


MAX_HOLD_CANDLES = 20


def run_backtest(symbol="BTCUSD"):

    df = get_history(
        symbol=symbol,
        resolution="5m",
        limit=1000
    )

    engine = BacktestEngine()

    for i in range(60, len(df) - MAX_HOLD_CANDLES):

        history = df.iloc[:i].copy()

        signal = generate_signal(history)

        if signal["signal"] == "WAIT":
            continue

        trade = create_trade(
            signal=signal["signal"],
            entry_price=signal["price"],
            atr=signal["atr"]
        )

        if trade is None:
            continue

        entry = trade["entry"]

        stop = trade["stop_loss"]

        target = trade["target"]

        exit_price = entry

        exit_reason = "TIME"

        for j in range(i + 1, i + MAX_HOLD_CANDLES):

            candle = df.iloc[j]

            high = float(candle["high"])

            low = float(candle["low"])

            close = float(candle["close"])

            if trade["signal"] in ["BUY", "STRONG BUY"]:

                if low <= stop:
                    exit_price = stop
                    exit_reason = "STOP LOSS"
                    break

                if high >= target:
                    exit_price = target
                    exit_reason = "TARGET"
                    break

            else:

                if high >= stop:
                    exit_price = stop
                    exit_reason = "STOP LOSS"
                    break

                if low <= target:
                    exit_price = target
                    exit_reason = "TARGET"
                    break

            exit_price = close

        engine.add_trade(
            symbol=symbol,
            signal=trade["signal"],
            entry=entry,
            stop_loss=stop,
            target=target,
            exit_price=exit_price,
            score=signal["score"],
            reasons=signal["reasons"] + [exit_reason]
        )

    engine.save_csv()

    print_report(engine.dataframe())


if __name__ == "__main__":

    run_backtest()
