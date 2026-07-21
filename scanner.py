from config import SYMBOLS
from history import get_multi_timeframe_history
from analysis.signal import generate_signal
from risk.trade_manager import create_trade
from database.logger import log_trade
from telegram import send_message
from notify import send_notification
from logger import logger
from broker.manager import broker

last_alerts = {}


def create_message(symbol, result, trade):
    return (
        f"NAKSHATRA AI\n"
        f"Symbol: {symbol}\n"
        f"Grade: {result['grade']}\n"
        f"Signal: {trade['signal']}\n"
        f"Confidence: {result['confidence']}%\n"
        f"Entry: {trade['entry']}\n"
        f"Stop Loss: {trade['stop_loss']}\n"
        f"TP1: {trade['tp1']}\n"
        f"TP2: {trade['tp2']}\n"
        f"TP3: {trade['tp3']}\n"
        f"Quantity: {trade['quantity']}\n"
        f"Risk Reward: {trade['risk_reward']}"
    )


def execute_trade(symbol, signal, trade):
    side = "sell" if "SELL" in signal.upper() else "buy"

    return broker.place_order(
        symbol=symbol,
        side=side,
        quantity=trade["quantity"],
        price=trade["entry"],
        order_type="market"
    )


def market_scan():

    logger.info("NAKSHATRA AI Scan Started")

    for symbol in SYMBOLS:

        try:

            data = get_multi_timeframe_history(symbol)

            if not data:
                continue

            result = generate_signal(data)

            signal = result["signal"]

            if signal == "WAIT":
                continue

            if result["grade"] not in ["A+", "A"]:
                logger.info(f"{symbol} skipped ({result['grade']})")
                continue

            if last_alerts.get(symbol) == signal:
                continue

            last_alerts[symbol] = signal

            trade = create_trade(
                signal=signal,
                entry_price=result["price"],
                atr=result["momentum"]["atr"]
            )

            if trade is None:
                continue

            logger.info(execute_trade(symbol, signal, trade))

            try:
                log_trade(
                    symbol=symbol,
                    signal_data=result,
                    trade=trade
                )
            except Exception as e:
                logger.exception(e)

            msg = create_message(symbol, result, trade)

            send_message(msg)

            send_notification(
                title=f"{symbol} {signal}",
                message=msg
            )

        except Exception as e:
            logger.exception(f"{symbol}: {e}")

    logger.info("NAKSHATRA AI Scan Finished")


def broker_health():
    try:
        return broker.health()
    except Exception as e:
        logger.exception(e)
        return False


if __name__ == "__main__":

    if broker_health():
        market_scan()
    else:
        logger.error("Broker Connection Failed")
