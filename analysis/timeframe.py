from history import get_history
from analysis.signal import generate_signal


TIMEFRAMES = [
    "5m",
    "15m",
    "1h",
    "4h"
]


def analyze_timeframes(symbol):

    result = {}

    for tf in TIMEFRAMES:

        try:

            df = get_history(
                symbol=symbol,
                resolution=tf,
                limit=200
            )

            signal = generate_signal(df)

            result[tf] = signal

        except Exception as e:

            result[tf] = {
                "signal": "ERROR",
                "score": 0,
                "error": str(e)
            }

    return result


def final_decision(results):

    buy = 0
    sell = 0
    wait = 0

    total_score = 0

    for tf in results.values():

        total_score += tf.get("score", 0)

        signal = tf.get("signal")

        if signal == "BUY":
            buy += 1

        elif signal == "SELL":
            sell += 1

        else:
            wait += 1

    if buy >= 3:
        final = "STRONG BUY"

    elif sell >= 3:
        final = "STRONG SELL"

    elif buy > sell:
        final = "BUY"

    elif sell > buy:
        final = "SELL"

    else:
        final = "WAIT"

    return {
        "decision": final,
        "score": total_score,
        "buy": buy,
        "sell": sell,
        "wait": wait
    }
