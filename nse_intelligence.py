"""NSE participant/FII-DII/sentiment intelligence with caching.
Uses NSE-published datasets through nselib. EOD positioning is labeled as such;
it is not a live order-flow feed.
"""
from __future__ import annotations
from datetime import date, timedelta
import math, threading, time

_CACHE = {}
_LOCK = threading.Lock()
TTL = 900


def _safe_records(df):
    if df is None:
        return []
    try:
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            work = df.copy()
            # Participant reports often use participant names as the index.
            if not isinstance(work.index, pd.RangeIndex):
                work = work.reset_index().rename(columns={"index": "participant"})
            out = work.where(pd.notna(work), None).to_dict(orient="records")
            return [{str(k): _clean(v) for k, v in r.items()} for r in out]
    except Exception:
        pass
    return []


def _clean(v):
    try:
        if hasattr(v, "item"):
            v = v.item()
    except Exception:
        pass
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def _cached(key, fn):
    now = time.time()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < TTL:
            return hit[1]
    try:
        value = fn()
    except Exception as exc:
        value = {"status": "ERROR", "error": str(exc)}
    with _LOCK:
        _CACHE[key] = (now, value)
    return value


def _last_report(fetcher, max_days=7):
    last_err = None
    start = date.today()
    for i in range(max_days):
        d = start - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        try:
            df = fetcher(d.strftime("%d-%m-%Y"))
            rows = _safe_records(df)
            if rows:
                return {"date": d.isoformat(), "rows": rows, "columns": list(rows[0].keys())}
        except Exception as exc:
            last_err = str(exc)
    return {"status": "NO DATA", "error": last_err or "No NSE report available"}


def _fii_dii():
    def load():
        try:
            from nselib import capital_market
            df = capital_market.fii_dii_trading_activity()
            rows = _safe_records(df)
            if not rows:
                return {"status": "NO DATA", "rows": []}
            normalized = []
            for r in rows:
                category = str(r.get("category") or r.get("Category") or "").upper()
                if "FII" in category or "DII" in category:
                    buy = r.get("buyValue", r.get("Buy Value"))
                    sell = r.get("sellValue", r.get("Sell Value"))
                    net = r.get("netValue", r.get("Net Value"))
                    normalized.append({"category": "FII/FPI" if "FII" in category else "DII", "date": r.get("date") or r.get("Date"), "buy_cr": _num(buy), "sell_cr": _num(sell), "net_cr": _num(net)})
            return {"status": "OK", "rows": normalized}
        except Exception as exc:
            return {"status": "ERROR", "rows": [], "error": str(exc)}
    return _cached("fii_dii", load)


def _participant_rows(df):
    rows = df if isinstance(df, list) else _safe_records(df)
    out = []
    for r in rows:
        def get(*names):
            for name in names:
                if name in r and r[name] is not None:
                    return _num(r[name])
                # tolerant normalized lookup
                nk = "".join(ch for ch in name.lower() if ch.isalnum())
                for k, v in r.items():
                    kk = "".join(ch for ch in str(k).lower() if ch.isalnum())
                    if kk == nk:
                        return _num(v)
            return None
        p = r.get("Client Type") or r.get("clientType") or r.get("Client_Type") or r.get("participant") or r.get("Participant")
        p = str(p or "").strip().upper()
        if not p:
            continue
        # NSE participant-wise OI schema: FII, DII, PRO, CLIENT.
        out.append({
            "participant": p,
            "future_index_long": get("Future Index Long", "Future_Index_Long"),
            "future_index_short": get("Future Index Short", "Future_Index_Short"),
            "future_stock_long": get("Future Stock Long", "Future_Stock_Long"),
            "future_stock_short": get("Future Stock Short", "Future_Stock_Short"),
            "index_call_long": get("Option Index Call Long", "Option_Index_Call_Long"),
            "index_call_short": get("Option Index Call Short", "Option_Index_Call_Short"),
            "index_put_long": get("Option Index Put Long", "Option_Index_Put_Long"),
            "index_put_short": get("Option Index Put Short", "Option_Index_Put_Short"),
        })
    return out

def _participant_oi():
    def load():
        try:
            from nselib import derivatives
            raw = _last_report(derivatives.participant_wise_open_interest)
            if raw.get("rows"):
                raw["rows"] = _participant_rows(raw["rows"])
            return raw
        except Exception as exc:
            return {"status": "ERROR", "error": str(exc), "rows": []}
    return _cached("participant_oi", load)


def _participant_volume():
    def load():
        try:
            from nselib import derivatives
            raw = _last_report(derivatives.participant_wise_trading_volume)
            return raw
        except Exception as exc:
            return {"status": "ERROR", "error": str(exc), "rows": []}
    return _cached("participant_volume", load)


def _india_vix():
    def load():
        try:
            from nselib import capital_market
            df = capital_market.india_vix_data(period="1M")
            rows = _safe_records(df)
            if not rows:
                return {"status": "NO DATA"}
            last = rows[-1]
            prev = rows[-2] if len(rows) > 1 else {}
            def first(r, *names):
                for n in names:
                    if n in r and r[n] is not None: return r[n]
                return None
            cur = _num(first(last,"CLOSE","Close","close","VIX"))
            pv = _num(first(prev,"CLOSE","Close","close","VIX")) if prev else 0
            return {"status":"OK","value":cur,"change":(cur-pv if cur and pv else None),"date":first(last,"DATE","Date","date")}
        except Exception as exc:
            return {"status":"ERROR","error":str(exc)}
    return _cached("india_vix", load)


def _num(v, default=None):
    try:
        x=float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _sentiment(fii_dii, vix):
    fii = next((x for x in fii_dii.get("rows",[]) if x.get("category")=="FII/FPI"), None)
    dii = next((x for x in fii_dii.get("rows",[]) if x.get("category")=="DII"), None)
    score=0.0; reasons=[]
    if fii and fii.get("net_cr") is not None:
        score += max(-2.0,min(2.0,fii["net_cr"]/5000.0))
        reasons.append(f"FII/FPI net ₹{fii['net_cr']:+,.0f} Cr")
    if dii and dii.get("net_cr") is not None:
        score += max(-1.5,min(1.5,dii["net_cr"]/5000.0))
        reasons.append(f"DII net ₹{dii['net_cr']:+,.0f} Cr")
    if vix.get("value") is not None:
        # Higher volatility is treated as risk-off pressure, not a direction forecast.
        score += -0.5 if vix["value"] >= 20 else 0.25 if vix["value"] < 14 else 0
        reasons.append(f"India VIX {vix['value']:.2f}")
    if score >= 0.8: bias="BULLISH"
    elif score <= -0.8: bias="BEARISH"
    else: bias="NEUTRAL"
    return {"status":"OK" if reasons else "NO DATA","bias":bias,"score":round(score,2),"reasons":reasons,"note":"Positioning-based sentiment; not a guaranteed next-session direction."}


def get_nse_intelligence(symbol="NIFTY50"):
    fii_dii=_fii_dii(); oi=_participant_oi(); vol=_participant_volume(); vix=_india_vix()
    return {"status":"OK","symbol":symbol,"as_of":fii_dii.get("rows",[{}])[-1].get("date") if fii_dii.get("rows") else oi.get("date"),"fii_dii":fii_dii,"participant_oi":oi,"participant_volume":vol,"india_vix":vix,"sentiment":_sentiment(fii_dii,vix)}
