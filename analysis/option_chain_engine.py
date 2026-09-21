"""Robust Indian option-chain engine.

Primary source: Kotak Neo option-chain API.
Fallback: NSE live option-chain through nselib.
No stale option signal is manufactured when both feeds fail.
"""
from datetime import datetime, timezone
import math
import re
import threading
import time

from delta import get_option_tickers
from market_registry import canonical_symbol, get_market
from kotak_neo_adaptor import get_option_chain as neo_get_option_chain

_CACHE = {}
_LOCK = threading.Lock()
TTL = 20


def _num(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _max_pain(rows):
    strikes = sorted({r["strike"] for r in rows if r.get("strike") is not None})
    if not strikes:
        return None
    best = min(
        strikes,
        key=lambda settlement: sum(
            (
                max(settlement - r["strike"], 0)
                if r["type"] == "CALL"
                else max(r["strike"] - settlement, 0)
            ) * r["oi"]
            for r in rows
        ),
    )
    return best


def _analyze_rows(symbol, rows, spot_price=None, expiry=None, source="unknown"):
    if not rows:
        return {
            "status": "NO DATA",
            "signal": "NEUTRAL",
            "confidence": 0,
            "reason": "No option-chain rows returned",
            "source": source,
            "rows": [],
        }

    calls = [r for r in rows if r["type"] == "CALL"]
    puts = [r for r in rows if r["type"] == "PUT"]
    if not calls or not puts:
        return {
            "status": "NO DATA",
            "signal": "NEUTRAL",
            "confidence": 0,
            "reason": f"Incomplete option chain: calls={len(calls)} puts={len(puts)}",
            "source": source,
            "rows": [],
        }

    call_oi = sum(_num(r.get("oi")) for r in calls)
    put_oi = sum(_num(r.get("oi")) for r in puts)
    call_vol = sum(_num(r.get("volume")) for r in calls)
    put_vol = sum(_num(r.get("volume")) for r in puts)
    pcr = put_oi / call_oi if call_oi else None
    volume_pcr = put_vol / call_vol if call_vol else None

    spot = _num(spot_price, 0)
    strikes = sorted({r["strike"] for r in rows if _num(r.get("strike")) > 0})
    atm = min(strikes, key=lambda k: abs(k - spot)) if strikes and spot > 0 else None
    call_res = max(calls, key=lambda r: _num(r.get("oi")), default=None)
    put_sup = max(puts, key=lambda r: _num(r.get("oi")), default=None)

    if pcr is None:
        signal = "NEUTRAL"
    elif pcr >= 1.10:
        signal = "BULLISH"
    elif pcr <= 0.90:
        signal = "BEARISH"
    else:
        signal = "SIDEWAYS"

    if atm is not None and signal == "SIDEWAYS":
        near = [r for r in rows if abs(r["strike"] - atm) <= max(abs(atm) * 0.03, 1)]
        nc = sum(_num(r.get("oi")) for r in near if r["type"] == "CALL")
        np = sum(_num(r.get("oi")) for r in near if r["type"] == "PUT")
        if nc and np:
            if np / nc >= 1.10:
                signal = "BULLISH"
            elif np / nc <= 0.90:
                signal = "BEARISH"

    confidence = min(95.0, 50.0 + abs(pcr - 1.0) * 100) if pcr is not None else 0
    top_calls = sorted(calls, key=lambda r: _num(r.get("oi")), reverse=True)[:5]
    top_puts = sorted(puts, key=lambda r: _num(r.get("oi")), reverse=True)[:5]

    return {
        "status": "OK",
        "signal": signal,
        "confidence": round(confidence, 1),
        "underlying": symbol,
        "source": source,
        "expiry": expiry,
        "spot": round(spot, 2) if spot else None,
        "atm_strike": atm,
        "pcr": round(pcr, 4) if pcr is not None else None,
        "volume_pcr": round(volume_pcr, 4) if volume_pcr is not None else None,
        "call_oi": round(call_oi, 2),
        "put_oi": round(put_oi, 2),
        "call_volume": round(call_vol, 2),
        "put_volume": round(put_vol, 2),
        "max_call_oi_resistance": call_res.get("strike") if call_res else None,
        "max_put_oi_support": put_sup.get("strike") if put_sup else None,
        "max_pain": _max_pain(rows),
        "top_call_oi": [
            {"strike": r["strike"], "oi": _num(r.get("oi")), "ltp": _num(r.get("ltp")), "oi_change": _num(r.get("oi_change"))}
            for r in top_calls
        ],
        "top_put_oi": [
            {"strike": r["strike"], "oi": _num(r.get("oi")), "ltp": _num(r.get("ltp")), "oi_change": _num(r.get("oi_change"))}
            for r in top_puts
        ],
        "rows": rows,
        "reason": f"PCR {pcr:.2f} • {source}" if pcr is not None else f"PCR unavailable • {source}",
    }


def _nselib_option_chain(symbol):
    mapping = {"NIFTY50": "NIFTY", "BANKNIFTY": "BANKNIFTY"}
    nse_symbol = mapping.get(symbol)
    if not nse_symbol:
        return None
    try:
        from nselib import derivatives
        df = derivatives.nse_live_option_chain(symbol=nse_symbol, oi_mode="compact")
        if df is None or getattr(df, "empty", True):
            return None

        cols = {re.sub(r"[^a-z0-9]", "", str(c).lower()): c for c in df.columns}

        def col(*names):
            for name in names:
                key = re.sub(r"[^a-z0-9]", "", name.lower())
                if key in cols:
                    return cols[key]
            return None

        strike_c = col("Strike_Price", "Strike Price", "strikePrice", "strike")
        c_oi = col("CALLS_OI", "CE_OI", "Call_OI")
        c_oi_chg = col("CALLS_Chng_in_OI", "CE_Chng_in_OI", "Call_OI_Change")
        c_vol = col("CALLS_Volume", "CE_Volume", "Call_Volume")
        c_ltp = col("CALLS_LTP", "CE_LTP", "Call_LTP")
        p_oi = col("PUTS_OI", "PE_OI", "Put_OI")
        p_oi_chg = col("PUTS_Chng_in_OI", "PE_Chng_in_OI", "Put_OI_Change")
        p_vol = col("PUTS_Volume", "PE_Volume", "Put_Volume")
        p_ltp = col("PUTS_LTP", "PE_LTP", "Put_LTP")
        exp_c = col("Expiry_Date", "Expiry Date", "expiry")

        if not strike_c or not c_oi or not p_oi:
            return None

        rows = []
        for _, r in df.iterrows():
            strike = _num(r.get(strike_c), None)
            if strike is None or strike <= 0:
                continue
            exp = r.get(exp_c) if exp_c else None
            rows.append({
                "symbol": f"{nse_symbol}-{strike:g}",
                "type": "CALL",
                "strike": strike,
                "oi": _num(r.get(c_oi)),
                "volume": _num(r.get(c_vol)),
                "ltp": _num(r.get(c_ltp)),
                "oi_change": _num(r.get(c_oi_chg)),
                "expiry": str(exp) if exp not in (None, "", "nan") else None,
            })
            rows.append({
                "symbol": f"{nse_symbol}-{strike:g}",
                "type": "PUT",
                "strike": strike,
                "oi": _num(r.get(p_oi)),
                "volume": _num(r.get(p_vol)),
                "ltp": _num(r.get(p_ltp)),
                "oi_change": _num(r.get(p_oi_chg)),
                "expiry": str(exp) if exp not in (None, "", "nan") else None,
            })

        expiry = next((r.get("expiry") for r in rows if r.get("expiry")), None)
        return rows, expiry
    except Exception:
        return None


def _kotak(symbol):
    try:
        payload = neo_get_option_chain(symbol)
        if isinstance(payload, dict):
            rows = payload.get("rows", [])
            expiry = payload.get("expiry")
        else:
            rows = payload or []
            expiry = None
        if rows:
            return rows, expiry
    except Exception:
        pass
    return None


def _delta(symbol, spot_price):
    underlying = "BTC" if symbol == "BTCUSD" else "ETH"
    raw = get_option_tickers(underlying)
    today = datetime.now(timezone.utc).date()
    parsed = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        sym = str(item.get("symbol") or "")
        ct = str(item.get("contract_type") or "").lower()
        typ = "CALL" if "call" in ct or sym.startswith("C-") else "PUT" if "put" in ct or sym.startswith("P-") else None
        m = re.search(r"^[CP]-[A-Z]+-([0-9.]+)-([0-9]{6})$", sym)
        strike = _num(item.get("strike_price"), None)
        expiry = None
        if m:
            strike = _num(m.group(1), strike)
            try:
                expiry = datetime.strptime(m.group(2), "%d%m%y").date()
            except Exception:
                pass
        if typ and strike is not None and expiry and expiry >= today:
            parsed.append((item, typ, strike, expiry))
    if not parsed:
        return {"status": "NO DATA", "signal": "NEUTRAL", "confidence": 0, "reason": "No current/future Delta options", "source": "delta"}
    expiry = min(x[3] for x in parsed)
    rows = []
    for item, typ, strike, exp in parsed:
        if exp != expiry:
            continue
        rows.append({"symbol": item.get("symbol"), "type": typ, "strike": strike, "oi": _num(item.get("oi")), "volume": _num(item.get("volume")), "ltp": _num(item.get("close") or item.get("mark_price")), "oi_change": _num(item.get("oi_change"))})
    return _analyze_rows(symbol, rows, spot_price, expiry.strftime("%d-%m-%Y"), "Delta")


def analyze_option_chain(symbol="BTCUSD", spot_price=None):
    symbol = canonical_symbol(symbol)
    market = get_market(symbol)
    key = (symbol, round(_num(spot_price), 2))
    now = time.time()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < TTL:
            return hit[1]

    result = None
    if market and market.get("provider") == "kotak_neo":
        kotak = _kotak(symbol)
        if kotak:
            rows, expiry = kotak
            result = _analyze_rows(symbol, rows, spot_price, expiry, "Kotak Neo")
        else:
            nse = _nselib_option_chain(symbol)
            if nse:
                rows, expiry = nse
                result = _analyze_rows(symbol, rows, spot_price, expiry, "NSE live")
            else:
                result = {"status":"NO DATA","signal":"NEUTRAL","confidence":0,"reason":"Kotak Neo and NSE option-chain feeds returned no data","source":"none","rows":[]}
    else:
        result = _delta(symbol, spot_price)

    with _LOCK:
        _CACHE[key] = (now, result)
    return result
