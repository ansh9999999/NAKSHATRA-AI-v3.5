from history import get_history
from analysis.signal import generate_signal


TIMEFRAMES = [
    "5m",
    "15m",
    "1h",
    "4h"
]


def analyze_timeframes(symbol):

    results = {}

    for tf in TIMEFRAMES:

        try:

            df = get_history(
                symbol=symbol,
                resolution=tf,
                limit=200
            )

            if df.empty:

                results[tf] = {
                    "signal": "WAIT",
                    "score": 0
                }

                continue

            signal = generate_signal(df)

            results[tf] = signal

        except Exception as e:

            results[tf] = {
                "signal": "ERROR",
                "score": 0,
                "error": str(e)
            }

    return results


def final_decision(results):

    buy = 0
    sell = 0
    wait = 0

    total_score = 0

    for tf in results.values():

        signal = tf.get("signal", "WAIT")

        total_score += tf.get("score", 0)

        if signal in ["BUY", "STRONG BUY"]:

            buy += 1

        elif signal in ["SELL", "STRONG SELL"]:

            sell += 1

        else:

            wait += 1

    if buy >= 3:

        decision = "BUY"

    elif sell >= 3:

        decision = "SELL"

    else:

        decision = "WAIT"

    return {

        "signal": decision,

        "score": total_score,

        "buy": buy,

        "sell": sell,

        "wait": wait,

        "details": results

                }
