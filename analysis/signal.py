"""NAKSHATRA AI signal engine with Indian option-chain + intraday trend."""
from __future__ import annotations

import math

from analysis.trend_engine import analyze_multi_timeframe
from analysis.momentum_engine import analyze_momentum
from analysis.smart_money_engine import analyze_smart_money
from analysis.confidence_engine import calculate_decision
from analysis.astrology_engine import analyze_astrology
from analysis.numerology_engine import analyze_numerology

INDIAN_OPTION_SYMBOLS = {"NIFTY50", "BANKNIFTY", "SENSEX", "NIFTYIT"}


def _num(v, default=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _option_chain_analysis(symbol: str, spot: float) -> dict:
    if symbol not in INDIAN_OPTION_SYMBOLS:
        return {"status": "NOT_APPLICABLE", "signal": "NEUTRAL", "confidence": 0,
                "reason": "Option chain is available for Indian index derivatives only."}
    try:
        # Use the same unified engine as /api/options so the dashboard and
        # decision engine cannot disagree about whether option-chain data exists.
        from analysis.option_chain_engine import analyze_option_chain
        return analyze_option_chain(symbol, spot_price=spot)
    except Exception as exc:
        return {"status": "ERROR", "signal": "NEUTRAL", "confidence": 0,
                "reason": f"Option-chain fetch failed: {exc}", "source": "exception", "rows": []}


def _intraday_summary(trend_result: dict) -> dict:
    tfs = ["5m", "15m", "1h"]
    items = []
    scores = []
    for tf in tfs:
        x = trend_result.get(tf, {}) or {}
        item = {"timeframe": tf, "trend": x.get("trend", "UNKNOWN"), "score": x.get("score", 0),
                "ema9": x.get("ema9", 0), "ema50": x.get("ema50", 0), "ema200": x.get("ema200", 0)}
        items.append(item)
        if item["trend"] != "UNKNOWN": scores.append(_num(item["score"]))
    avg = sum(scores) / len(scores) if scores else 0
    if avg >= 30: overall = "STRONG BULL"
    elif avg >= 10: overall = "BULL"
    elif avg <= -30: overall = "STRONG BEAR"
    elif avg <= -10: overall = "BEAR"
    else: overall = "SIDEWAYS"
    return {"overall": overall, "score": round(avg, 1), "timeframes": items}


def generate_signal(data):
    entry_df = data["5m"]
    if entry_df.empty:
        return {"recommendation": "NO DATA", "overall_confidence": 0}

    symbol = str(data.get("symbol", "BTCUSD")).upper()
    trend_data = {tf: data[tf] for tf in ("5m", "15m", "1h", "1d") if tf in data}
    trend_result = analyze_multi_timeframe(trend_data)
    momentum_result = analyze_momentum(entry_df)
    smart_money_result = analyze_smart_money(entry_df)

    raw_technical = (
        trend_result["total_score"]
        + momentum_result["score"]
        + smart_money_result["score"]
    )
    technical_score = max(0, min(100, abs(raw_technical)))
    if raw_technical >= 25:
        technical_signal = "BUY"
    elif raw_technical <= -25:
        technical_signal = "SELL"
    else:
        technical_signal = "NEUTRAL"
    technical_result = {
        "signal": technical_signal, "confidence": technical_score, "trend": trend_result,
        "momentum": momentum_result, "smart_money": smart_money_result,
        "reasons": trend_result["reasons"] + momentum_result["reasons"] + smart_money_result["reasons"],
    }

    timestamp = entry_df.index[-1]
    if hasattr(timestamp, "to_pydatetime"):
        timestamp = timestamp.to_pydatetime()

    spot = _num(entry_df["close"].iloc[-1])
    option_chain = _option_chain_analysis(symbol, spot)
    intraday = _intraday_summary(trend_result)
    astrology_result = analyze_astrology(timestamp)
    numerology_result = analyze_numerology(timestamp, symbol)

    result = calculate_decision(technical_result, astrology_result, numerology_result, option_chain)

    # Data-quality gate: for Indian index decisions, a live CE+PE option-chain
    # is a required confirmation layer. Never present a BUY/SELL as actionable
    # when that feed is unavailable. This also prevents a missing chain from
    # being silently replaced by fallback weights in confidence_engine.py.
    if symbol in INDIAN_OPTION_SYMBOLS:
        oc_status = str((option_chain or {}).get("status", "NO DATA")).upper()
        if oc_status != "OK":
            result["recommendation"] = "WAIT"
            result["overall_confidence"] = min(float(result.get("overall_confidence", 0) or 0), 25.0)
            result["agreement"] = "DATA RISK"
            result["data_quality"] = {
                "status": "BLOCKED",
                "required": ["5m candles", "live option chain (CE+PE)"],
                "missing": ["live option chain (CE+PE)"],
                "message": "WAIT — live NSE/Kotak option-chain confirmation is unavailable.",
            }
        else:
            result["data_quality"] = {
                "status": "OK",
                "required": ["5m candles", "live option chain (CE+PE)"],
                "missing": [],
                "message": "Required decision inputs available.",
            }

    result["symbol"] = symbol
    result["price"] = spot
    result["time"] = str(timestamp)
    result["technical"] = technical_result
    result["astrology"] = astrology_result
    result["numerology"] = numerology_result
    result["option_chain"] = option_chain
    result["intraday_trend"] = intraday

    # Keep existing 3-module decision intact, but expose an explicit
    # option-chain agreement instead of silently ignoring the chain.
    result["agreement"] = result.get("agreement", "PARTIAL AGREEMENT")

    # Explicit, data-driven trade setup. A WAIT state still tells the user
    # exactly what confirmation is required instead of leaving the card blank.
    atr_value = _num(momentum_result.get("atr"), 0)
    last = spot
    recent_high = _num(entry_df["high"].tail(3).max(), last)
    recent_low = _num(entry_df["low"].tail(3).min(), last)
    oc = option_chain if isinstance(option_chain, dict) else {}
    support = _num(oc.get("max_put_oi_support"), 0)
    resistance = _num(oc.get("max_call_oi_resistance"), 0)
    direction = str(result.get("direction", "NEUTRAL")).upper()
    recommendation = str(result.get("recommendation", "WAIT")).upper()
    buffer = max(0.05, atr_value * 0.10) if atr_value > 0 else max(0.05, last * 0.0002)

    if recommendation == "BUY" and atr_value > 0:
        entry = max(last, recent_high, resistance if resistance > last else 0) + buffer
        sl = entry - 1.2 * atr_value
        t1 = entry + 1.5 * (entry - sl)
        t2 = entry + 2.5 * (entry - sl)
        t3 = entry + 3.5 * (entry - sl)
        result["trade_plan"] = {
            "status": "READY", "side": "BUY", "entry_zone": f"{entry:.2f} or above",
            "entry_trigger": round(entry, 2), "stop_loss": round(sl, 2),
            "target1": round(t1, 2), "target2": round(t2, 2), "target3": round(t3, 2),
            "risk_reward": "1 : 1.5 / 2.5 / 3.5",
            "when": "After a 5m candle closes above the trigger with volume confirmation",
            "basis": "AI direction + 5m structure + ATR"
        }
    elif recommendation == "SELL" and atr_value > 0:
        entry = min(last, recent_low, support if support > 0 and support < last else last) - buffer
        sl = entry + 1.2 * atr_value
        t1 = entry - 1.5 * (sl - entry)
        t2 = entry - 2.5 * (sl - entry)
        t3 = entry - 3.5 * (sl - entry)
        result["trade_plan"] = {
            "status": "READY", "side": "SELL", "entry_zone": f"{entry:.2f} or below",
            "entry_trigger": round(entry, 2), "stop_loss": round(sl, 2),
            "target1": round(t1, 2), "target2": round(t2, 2), "target3": round(t3, 2),
            "risk_reward": "1 : 1.5 / 2.5 / 3.5",
            "when": "After a 5m candle closes below the trigger with volume confirmation",
            "basis": "AI direction + 5m structure + ATR"
        }
    else:
        if direction == "BULLISH":
            trigger = max(recent_high, resistance if resistance > last else 0) + buffer
            when = f"WAIT now • BUY only after 5m close above {trigger:.2f} + volume confirmation"
        elif direction == "BEARISH":
            trigger = min(recent_low, support if support > 0 and support < last else last) - buffer
            when = f"WAIT now • SELL only after 5m close below {trigger:.2f} + volume confirmation"
        else:
            when = "WAIT now • No trade until 5m and 15m direction align with volume"
        result["trade_plan"] = {
            "status": "WAIT", "side": "WAIT", "entry_zone": "—",
            "stop_loss": None, "target1": None, "target2": None, "target3": None,
            "risk_reward": "—", "when": when,
            "basis": "No high-quality confirmed entry yet"
        }

    return result
