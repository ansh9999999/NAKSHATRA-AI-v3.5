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
        from kotak_neo_adaptor import get_option_chain
        rows = get_option_chain(symbol)
    except Exception as exc:
        return {"status": "ERROR", "signal": "NEUTRAL", "confidence": 0,
                "reason": f"Option-chain fetch failed: {exc}"}

    if not rows:
        return {"status": "NO DATA", "signal": "NEUTRAL", "confidence": 0,
                "reason": "Kotak Neo returned no option-chain rows."}

    calls = [r for r in rows if str(r.get("type", "")).upper() == "CALL"]
    puts = [r for r in rows if str(r.get("type", "")).upper() == "PUT"]
    if not calls or not puts:
        return {"status": "NO DATA", "signal": "NEUTRAL", "confidence": 0,
                "reason": f"Incomplete option chain: calls={len(calls)} puts={len(puts)}"}

    call_oi = sum(_num(r.get("oi")) for r in calls)
    put_oi = sum(_num(r.get("oi")) for r in puts)
    call_vol = sum(_num(r.get("volume")) for r in calls)
    put_vol = sum(_num(r.get("volume")) for r in puts)
    pcr = put_oi / call_oi if call_oi else 0.0
    volume_pcr = put_vol / call_vol if call_vol else 0.0

    strikes = sorted({round(_num(r.get("strike")), 2) for r in rows if _num(r.get("strike")) > 0})
    atm = min(strikes, key=lambda s: abs(s - spot)) if strikes and spot > 0 else (strikes[len(strikes)//2] if strikes else 0)

    max_put = max(puts, key=lambda r: _num(r.get("oi")), default={})
    max_call = max(calls, key=lambda r: _num(r.get("oi")), default={})
    support = _num(max_put.get("strike"))
    resistance = _num(max_call.get("strike"))

    # Standard max-pain calculation over the available strikes.
    max_pain = None
    best_loss = None
    for settlement in strikes:
        loss = 0.0
        for r in calls:
            loss += max(0.0, settlement - _num(r.get("strike"))) * _num(r.get("oi"))
        for r in puts:
            loss += max(0.0, _num(r.get("strike")) - settlement) * _num(r.get("oi"))
        if best_loss is None or loss < best_loss:
            best_loss, max_pain = loss, settlement

    score = 0
    reasons = []
    if pcr >= 1.20:
        score += 25; reasons.append(f"PCR {pcr:.2f} is bullish")
    elif pcr >= 1.00:
        score += 10; reasons.append(f"PCR {pcr:.2f} mildly bullish")
    elif pcr <= 0.75:
        score -= 25; reasons.append(f"PCR {pcr:.2f} is bearish")
    elif pcr < 1.00:
        score -= 10; reasons.append(f"PCR {pcr:.2f} mildly bearish")

    if volume_pcr >= 1.10:
        score += 10; reasons.append(f"Volume PCR {volume_pcr:.2f} supports buyers")
    elif volume_pcr <= 0.80:
        score -= 10; reasons.append(f"Volume PCR {volume_pcr:.2f} supports sellers")

    if spot and support and spot > support:
        reasons.append(f"Put OI support {support:g} below spot")
    if spot and resistance and spot < resistance:
        reasons.append(f"Call OI resistance {resistance:g} above spot")

    score = max(-35, min(35, score))
    if score >= 20:
        signal = "BUY"
    elif score <= -20:
        signal = "SELL"
    else:
        signal = "NEUTRAL"

    confidence = int(round(abs(score) / 35 * 100))
    top_call = sorted(calls, key=lambda r: _num(r.get("oi")), reverse=True)[:5]
    top_put = sorted(puts, key=lambda r: _num(r.get("oi")), reverse=True)[:5]
    near_strikes = sorted(strikes, key=lambda s: abs(s - atm))[:11]
    by_strike = {}
    for r in rows:
        by_strike.setdefault(_num(r.get("strike")), {})[str(r.get("type", "")).upper()] = r
    atm_chain = []
    for strike in sorted(near_strikes):
        c = by_strike.get(strike, {}).get("CALL", {})
        p = by_strike.get(strike, {}).get("PUT", {})
        atm_chain.append({
            "strike": strike,
            "call_ltp": _num(c.get("ltp")), "call_oi": round(_num(c.get("oi"))),
            "call_volume": round(_num(c.get("volume"))),
            "put_ltp": _num(p.get("ltp")), "put_oi": round(_num(p.get("oi"))),
            "put_volume": round(_num(p.get("volume"))),
            "atm": abs(strike-atm) < 0.001,
        })

    return {
        "status": "OK",
        "signal": signal,
        "confidence": confidence,
        "reason": " • ".join(reasons[:4]) or "Live Kotak Neo option-chain data",
        "expiry": rows[0].get("expiry"),
        "pcr": round(pcr, 3),
        "volume_pcr": round(volume_pcr, 3),
        "atm_strike": atm,
        "max_put_oi_support": support,
        "max_call_oi_resistance": resistance,
        "max_pain": max_pain,
        "call_oi": round(call_oi),
        "put_oi": round(put_oi),
        "call_volume": round(call_vol),
        "put_volume": round(put_vol),
        "top_call_oi": [{"strike": _num(r.get("strike")), "oi": round(_num(r.get("oi"))), "ltp": _num(r.get("ltp"))} for r in top_call],
        "top_put_oi": [{"strike": _num(r.get("strike")), "oi": round(_num(r.get("oi"))), "ltp": _num(r.get("ltp"))} for r in top_put],
        "atm_chain": atm_chain,
        "rows": rows,
    }


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

    technical_score = max(0, min(100, abs(
        trend_result["total_score"] + momentum_result["score"] + smart_money_result["score"]
    )))
    technical_signal = "BUY" if technical_score >= 85 else "SELL" if technical_score <= 25 else "NEUTRAL"
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

    result = calculate_decision(technical_result, astrology_result, numerology_result)
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
    return result
