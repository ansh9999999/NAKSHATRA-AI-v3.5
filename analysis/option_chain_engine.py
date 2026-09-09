"""Provider-aware full option-chain analysis for crypto and Indian markets."""
from datetime import datetime, timezone
import math
import re

from delta import get_option_tickers
from market_registry import canonical_symbol, get_market
from kotak_neo_adapter import get_option_chain as neo_get_option_chain


def _num(v, default=0.0):
    try:
        x = float(v); return x if math.isfinite(x) else default
    except Exception:
        return default


def _max_pain(rows):
    strikes = sorted({r["strike"] for r in rows if r.get("strike") is not None})
    if not strikes: return None
    best = min(strikes, key=lambda settlement: sum((max(settlement-r["strike"],0) if r["type"]=="CALL" else max(r["strike"]-settlement,0))*r["oi"] for r in rows))
    return best


def _analyze_rows(symbol, rows, spot_price=None, expiry=None):
    if not rows:
        return {"status":"NO DATA","signal":"NEUTRAL","confidence":0,"reason":"No option-chain rows returned"}
    calls = [r for r in rows if r["type"] == "CALL"]
    puts = [r for r in rows if r["type"] == "PUT"]
    call_oi = sum(_num(r.get("oi")) for r in calls); put_oi = sum(_num(r.get("oi")) for r in puts)
    call_vol = sum(_num(r.get("volume")) for r in calls); put_vol = sum(_num(r.get("volume")) for r in puts)
    pcr = put_oi / call_oi if call_oi else None; volume_pcr = put_vol / call_vol if call_vol else None
    spot = _num(spot_price, 0)
    strikes = sorted({r["strike"] for r in rows}); atm = min(strikes,key=lambda k:abs(k-spot)) if strikes and spot>0 else None
    call_res = max(calls,key=lambda r:_num(r.get("oi")),default=None); put_sup=max(puts,key=lambda r:_num(r.get("oi")),default=None)
    if pcr is None: signal="NEUTRAL"
    elif pcr >= 1.10: signal="BULLISH"
    elif pcr <= 0.90: signal="BEARISH"
    else: signal="SIDEWAYS"
    if atm is not None and signal == "SIDEWAYS":
        near=[r for r in rows if abs(r["strike"]-atm)<=max(abs(atm)*0.03,1)]
        nc=sum(_num(r.get("oi")) for r in near if r["type"]=="CALL"); np=sum(_num(r.get("oi")) for r in near if r["type"]=="PUT")
        if nc and np:
            if np/nc >= 1.10: signal="BULLISH"
            elif np/nc <= 0.90: signal="BEARISH"
    confidence=min(95.0,50.0+abs(pcr-1.0)*100) if pcr is not None else 0
    return {"status":"OK","signal":signal,"confidence":round(confidence,1),"underlying":symbol,"expiry":expiry,"spot":round(spot,2) if spot else None,"atm_strike":atm,"pcr":round(pcr,4) if pcr is not None else None,"volume_pcr":round(volume_pcr,4) if volume_pcr is not None else None,"call_oi":round(call_oi,2),"put_oi":round(put_oi,2),"call_volume":round(call_vol,2),"put_volume":round(put_vol,2),"max_call_oi_resistance":call_res.get("strike") if call_res else None,"max_put_oi_support":put_sup.get("strike") if put_sup else None,"max_pain":_max_pain(rows),"top_call_oi":[{"strike":r["strike"],"oi":_num(r.get("oi"))} for r in sorted(calls,key=lambda x:_num(x.get("oi")),reverse=True)[:5]],"top_put_oi":[{"strike":r["strike"],"oi":_num(r.get("oi"))} for r in sorted(puts,key=lambda x:_num(x.get("oi")),reverse=True)[:5]],"rows":len(rows),"reason":f"PCR {pcr:.2f}" if pcr is not None else "PCR unavailable"}


def _delta(symbol, spot_price):
    underlying = "BTC" if symbol == "BTCUSD" else "ETH"
    raw = get_option_tickers(underlying)
    today = datetime.now(timezone.utc).date(); parsed=[]
    for item in raw or []:
        if not isinstance(item,dict): continue
        sym=str(item.get("symbol") or ""); ct=str(item.get("contract_type") or "").lower()
        typ="CALL" if "call" in ct or sym.startswith("C-") else "PUT" if "put" in ct or sym.startswith("P-") else None
        m=re.search(r"^[CP]-[A-Z]+-([0-9.]+)-([0-9]{6})$",sym)
        strike=_num(item.get("strike_price"),None)
        expiry=None
        if m:
            strike=_num(m.group(1),strike)
            try: expiry=datetime.strptime(m.group(2),"%d%m%y").date()
            except Exception: pass
        if typ and strike is not None and expiry and expiry>=today: parsed.append((item,typ,strike,expiry))
    if not parsed: return {"status":"NO DATA","signal":"NEUTRAL","confidence":0,"reason":"No current/future Delta options"}
    expiry=min(x[3] for x in parsed); rows=[]
    for item,typ,strike,exp in parsed:
        if exp!=expiry: continue
        rows.append({"symbol":item.get("symbol"),"type":typ,"strike":strike,"oi":_num(item.get("oi")),"volume":_num(item.get("volume"))})
    return _analyze_rows(symbol,rows,spot_price,expiry.strftime("%d-%m-%Y"))


def analyze_option_chain(symbol="BTCUSD", spot_price=None):
    symbol=canonical_symbol(symbol); market=get_market(symbol)
    try:
        if market and market.get("provider") == "kotak_neo":
            payload=neo_get_option_chain(symbol,spot_price)
            return _analyze_rows(symbol,payload.get("rows",[]),spot_price,payload.get("expiry") or None)
        return _delta(symbol,spot_price)
    except Exception as exc:
        return {"status":"ERROR","signal":"NEUTRAL","confidence":0,"reason":str(exc)}
