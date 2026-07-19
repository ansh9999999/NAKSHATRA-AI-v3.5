# scanner.py replacement
"""
NAKSHATRA AI
Market Scanner
"""

from config import SYMBOLS
from history import get_history
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
        f"Signal: {trade['signal']}\n"
        f"Entry: {trade['entry']}\n"
        f"Stop Loss: {trade['stop_loss']}\n"
        f"TP1: {trade['tp1']}\n"
        f"TP2: {trade['tp2']}\n"
        f"TP3: {trade['tp3']}\n"
        f"Quantity: {trade['quantity']}\n"
        f"Risk Reward: {trade['risk_reward']}\n"
        f"Trend: {result.get('trend','')}\n"
        f"Volume: {result.get('volume_status','')}\n"
        f"Liquidity: {result.get('liquidity','')}\n"
        f"Score: {result.get('score','')}"
    )

def execute_trade(symbol, signal, trade):
    side="sell" if "SELL" in signal.upper() else "buy"
    return broker.place_order(symbol=symbol,side=side,quantity=trade["quantity"],price=trade["entry"],order_type="market")

def market_scan():
    logger.info("NAKSHATRA AI Scan Started")
    for symbol in SYMBOLS:
        try:
            df=get_history(symbol)
            if df.empty:
                continue
            result=generate_signal(df)
            signal=result.get("signal","WAIT")
            if signal=="WAIT":
                continue
            if last_alerts.get(symbol)==signal:
                continue
            last_alerts[symbol]=signal
            trade=create_trade(signal=signal,entry_price=result["price"],atr=result["atr"])
            if trade is None:
                continue
            logger.info(execute_trade(symbol,signal,trade))
            try:
                log_trade(symbol=symbol,signal_data=result,trade=trade)
            except Exception as e:
                logger.exception(e)
            msg=create_message(symbol,result,trade)
            send_message(msg)
            send_notification(title=f"{symbol} {signal}",message=msg)
        except Exception as e:
            logger.exception(f"{symbol}: {e}")
    logger.info("NAKSHATRA AI Scan Finished")

def broker_health():
    try:
        return broker.health()
    except Exception as e:
        logger.exception(e)
        return False

if __name__=="__main__":
    if broker_health():
        market_scan()
    else:
        logger.error("Broker Connection Failed")
