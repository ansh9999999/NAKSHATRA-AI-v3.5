from config import SYMBOLS

from history import get_history

from analysis.signal import generate_signal

from telegram import send_message

from notify import send_notification

from logger import logger

from risk.trade_manager import create_trade

from database.logger import log_trade


last_alerts = {}


def market_scan():

    logger.info("========== NAKSHATRA AI Scan Started ==========")

    for symbol in SYMBOLS:

        try:

            df = get_history(symbol)

            if df.empty:
                logger.warning(f"{symbol}: No Market Data")
                continue

            result = generate_signal(df)

            signal = result["signal"]

            if signal == "WAIT":
                logger.info(f"{symbol}: WAIT")
                continue

            previous = last_alerts.get(symbol)

            if previous == signal:
                logger.info(f"{symbol}: Duplicate Alert")
                continue

            last_alerts[symbol] = signal

            trade = create_trade(
                signal=signal,
                entry_price=result["price"],
                atr=result["atr"]
            )

            if trade is None:
                continue

            # Save trade in database
            try:
                log_trade(
                    symbol=symbol,
                    signal_data=result,
                    trade=trade
                )
                logger.info(f"{symbol}: Trade Saved")
            except Exception as db_error:
                logger.exception(f"{symbol}: Database Error: {db_error}")

            message = f"""
🚀 NAKSHATRA AI

📊 Symbol : {symbol}

🎯 Signal : {trade['signal']}

💰 Entry : {trade['entry']}

🛑 Stop Loss : {trade['stop_loss']}

🎯 TP1 : {trade['tp1']}

🎯 TP2 : {trade['tp2']}

🎯 TP3 : {trade['tp3']}

📦 Qty : {trade['quantity']}

⚖ RR : {trade['risk_reward']}

📈 Trend : {result['trend']}

📊 Volume : {result['volume_status']}

💧 Liquidity : {result['liquidity']}

⭐ Score : {result['score']}
"""

            telegram_ok = send_message(message)

            if telegram_ok:
                logger.info(f"{symbol}: Telegram Sent")
            else:
                logger.warning(f"{symbol}: Telegram Failed")

            notify_ok = send_notification(
                title=f"{symbol} {signal}",
                message=message
            )

            if notify_ok:
                logger.info(f"{symbol}: ntfy Sent")
            else:
                logger.warning(f"{symbol}: ntfy Failed")

        except Exception as e:
            logger.exception(f"{symbol}: {e}")

    logger.info("========== Scan Finished ==========")


if __name__ == "__main__":
    market_scan()
