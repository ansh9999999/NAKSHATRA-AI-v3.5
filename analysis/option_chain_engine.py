"""Robust Indian/Delta option-chain engine.

Indian markets:
    1) NSE live option chain via nselib (primary)
    2) Kotak Neo option chain (secondary fallback)

The engine never fabricates a chain. If NSE/Kotak return no usable CE+PE rows,
status is NO DATA and downstream AI must treat the option signal as unavailable.
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
TTL = 15


def _num(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _clean_expiry(v):
    if v is None:
        return None
    if hasattr(v, "to_pydatetime"):
        try:
            v = v.to_pydatetime()
        except Exception:
            pass
    if hasattr(v, "strftime"):
        try:
            return v.strftime("%d-%m-%Y")
        except Exception:
            pass
    s = str(v).strip()
    if not s or s.lower() in {"nan", "nat", "none"}:
        return None
    # Normalise common NSE formats to DD-MM-YYYY when possible.
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(s[:10] if fmt == "%Y-%m-%d" else s, fmt).strftime("%d-%m-%Y")
        except Exception:
            pass
    return s


def _expiry_candidates(derivatives):
    """Return upcoming index-option expiries in a tolerant format."""
    try:
        raw = derivatives.expiry_dates_option_index()
    except Exception:
        return []

    values = []
    if raw is None:
        return values
    if hasattr(raw, "columns") and hasattr(raw, "iterrows"):
        cols = list(raw.columns)
        preferred = None
        for c in cols:
            key = re.sub(r"[^a-z0-9]", "", str(c).lower())
            if "expiry" in key or key in {"date", "expirydate"}:
                preferred = c
                break
        if preferred is not None:
            values = raw[preferred].tolist()
        else:
            values = raw.iloc[:, 0].tolist() if len(cols) else []
    elif isinstance(raw, dict):
        for key in ("expiry_dates", "expiries", "data", "records", "dates"):
            if key in raw:
                raw = raw[key]
                break
        values = raw if isinstance(raw, (list, tuple, set)) else [raw]
    elif isinstance(raw, (list, tuple, set)):
        values = list(raw)
    else:
        values = [raw]

    out = []
    today = datetime.now().date()
    for value in values:
        exp = _clean_expiry(value)
        if not exp:
            continue
        try:
            d = datetime.strptime(exp, "%d-%m-%Y").date()
            if d >= today and exp not in out:
                out.append(exp)
        except Exception:
            if exp not in out:
                out.append(exp)
    return out[:6]


def _max_pain(rows):
    strikes = sorted({r["strike"] for r in rows if r.get("strike") is not None})
    if not strikes:
        return None
    return min(
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


def _no_data(reason, source="none", expiry=None):
    return {
        "status": "NO DATA",
        "signal": "NEUTRAL",
        "confidence": 0,
        "reason": reason,
        "source": source,
        "expiry": expiry,
        "rows": [],
    }


def _analyze_rows(symbol, rows, spot_price=None, expiry=None, source="unknown"):
    if not rows:
        return _no_data("No usable option-chain rows returned", source, expiry)

    calls = [r for r in rows if r["type"] == "CALL"]
    puts = [r for r in rows if r["type"] == "PUT"]
    if not calls or not puts:
        return _no_data(
            f"Incomplete option chain: calls={len(calls)} puts={len(puts)}",
            source,
            expiry,
        )

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

    confidence = min(95.0, 50.0 + abs(pcr - 1.0) * 100) if pcr is not None else 0
    top_calls = sorted(calls, key=lambda r: _num(r.get("oi")), reverse=True)[:5]
    top_puts = sorted(puts, key=lambda r: _num(r.get("oi")), reverse=True)[:5]

    from analysis.gamma_squeeze_engine import detect_squeeze
    squeeze = detect_squeeze(symbol, rows, spot, expiry)

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
        "row_count": len(rows),
        "gamma_squeeze": squeeze,
        "reason": f"PCR {pcr:.2f} • {source}" if pcr is not None else f"PCR unavailable • {source}",
    }


def _nselib_option_chain(symbol):
    mapping = {"NIFTY50": "NIFTY", "BANKNIFTY": "BANKNIFTY"}
    nse_symbol = mapping.get(symbol)
    if not nse_symbol:
        return None

    try:
        from nselib import derivatives
    except Exception:
        return None

    # Try nearest explicit expiry first. This avoids relying on an implicit
    # expiry when NSE changes the default contract returned by the library.
    expiries = _expiry_candidates(derivatives)
    attempts = []
    if expiries:
        attempts.extend(expiries[:3])
    attempts.append(None)

    for expiry in attempts:
        try:
            kwargs = {"symbol": nse_symbol, "oi_mode": "full"}
            if expiry:
                kwargs["expiry_date"] = expiry
            df = derivatives.nse_live_option_chain(**kwargs)
            if df is None or getattr(df, "empty", True):
                continue

            cols = {re.sub(r"[^a-z0-9]", "", str(c).lower()): c for c in df.columns}

            def col(*names):
                for name in names:
                    key = re.sub(r"[^a-z0-9]", "", name.lower())
                    if key in cols:
                        return cols[key]
                return None

            strike_c = col("Strike_Price", "Strike Price", "strikePrice", "strike", "STRIKE_PRICE")
            c_oi = col("CALLS_OI", "CE_OI", "Call_OI", "CALL_OI")
            c_oi_chg = col("CALLS_Chng_in_OI", "CE_Chng_in_OI", "Call_OI_Change", "CALLS_CHANGE_IN_OI")
            c_vol = col("CALLS_Volume", "CE_Volume", "Call_Volume", "CALLS_VOLUME")
            c_ltp = col("CALLS_LTP", "CE_LTP", "Call_LTP", "CALLS_LAST_PRICE")
            c_iv = col("CALLS_IV", "CE_IV", "Call_IV")
            p_oi = col("PUTS_OI", "PE_OI", "Put_OI", "PUT_OI")
            p_oi_chg = col("PUTS_Chng_in_OI", "PE_Chng_in_OI", "Put_OI_Change", "PUTS_CHANGE_IN_OI")
            p_vol = col("PUTS_Volume", "PE_Volume", "Put_Volume", "PUTS_VOLUME")
            p_ltp = col("PUTS_LTP", "PE_LTP", "Put_LTP", "PUTS_LAST_PRICE")
            p_iv = col("PUTS_IV", "PE_IV", "Put_IV")
            exp_c = col("Expiry_Date", "Expiry Date", "expiry", "EXPIRY_DATE")

            if not strike_c or not c_oi or not p_oi:
                continue

            rows = []
            for _, r in df.iterrows():
                strike = _num(r.get(strike_c), None)
                if strike is None or strike <= 0:
                    continue
                exp = _clean_expiry(r.get(exp_c)) if exp_c else expiry
                rows.append({
                    "symbol": f"{nse_symbol}-{strike:g}", "type": "CALL", "strike": strike,
                    "oi": _num(r.get(c_oi)), "volume": _num(r.get(c_vol)), "ltp": _num(r.get(c_ltp)),
                    "oi_change": _num(r.get(c_oi_chg)), "iv": _num(r.get(c_iv)), "expiry": exp,
                })
                rows.append({
                    "symbol": f"{nse_symbol}-{strike:g}", "type": "PUT", "strike": strike,
                    "oi": _num(r.get(p_oi)), "volume": _num(r.get(p_vol)), "ltp": _num(r.get(p_ltp)),
                    "oi_change": _num(r.get(p_oi_chg)), "iv": _num(r.get(p_iv)), "expiry": exp,
                })

            if rows:
                final_expiry = expiry or next((r.get("expiry") for r in rows if r.get("expiry")), None)
                return rows, final_expiry
        except Exception:
            continue
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
            return rows, _clean_expiry(expiry)
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
        return _no_data("No current/future Delta options", "Delta")
    expiry = min(x[3] for x in parsed)
    rows = []
    for item, typ, strike, exp in parsed:
        if exp != expiry:
            continue
        rows.append({
            "symbol": item.get("symbol"), "type": typ, "strike": strike,
            "oi": _num(item.get("oi")), "volume": _num(item.get("volume")),
            "ltp": _num(item.get("close") or item.get("mark_price")),
            "oi_change": _num(item.get("oi_change")),
        })
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
        # NSE is primary for the dashboard because it is the exchange-native
        # index option-chain source. Kotak remains a secondary fallback.
        nse = _nselib_option_chain(symbol)
        if nse:
            rows, expiry = nse
            result = _analyze_rows(symbol, rows, spot_price, expiry, "NSE")
        else:
            kotak = _kotak(symbol)
            if kotak:
                rows, expiry = kotak
                result = _analyze_rows(symbol, rows, spot_price, expiry, "Kotak Neo")
            else:
                result = _no_data(
                    "NSE live option-chain and Kotak Neo returned no usable CE/PE rows",
                    "none",
                )
    else:
        result = _delta(symbol, spot_price)

    with _LOCK:
        _CACHE[key] = (now, result)
    return result
