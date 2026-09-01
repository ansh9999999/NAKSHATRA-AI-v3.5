"""NAKSHATRA AI - Delta public option-chain analysis.

Uses Delta Exchange's public ticker data for calls/puts. No private API
credentials are required. The engine is deliberately transparent: it
reports the raw OI/volume totals and derives PCR, support/resistance and
max-pain from those values.
"""

from datetime import datetime, timezone
import math
import re

from delta import get_option_tickers


def _num(v, default=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _expiry_from_item(item):
    value = item.get("expiry") or item.get("expiry_date")
    if value:
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d%m%y"):
            try:
                return datetime.strptime(str(value), fmt).date()
            except Exception:
                pass

    symbol = str(item.get("symbol") or "")
    m = re.search(r"^[CP]-[A-Z]+-[0-9.]+-(\d{6})$", symbol)
    if m:
        try:
            return datetime.strptime(m.group(1), "%d%m%y").date()
        except Exception:
            pass
    return None


def _strike(item):
    value = item.get("strike_price")
    if value is not None:
        return _num(value, None)
    symbol = str(item.get("symbol") or "")
    m = re.search(r"^[CP]-[A-Z]+-([0-9.]+)-\d{6}$", symbol)
    return _num(m.group(1), None) if m else None


def _kind(item):
    ct = str(item.get("contract_type") or "").lower()
    symbol = str(item.get("symbol") or "").upper()
    if "call" in ct or symbol.startswith("C-"):
        return "CALL"
    if "put" in ct or symbol.startswith("P-"):
        return "PUT"
    return None


def _max_pain(rows):
    strikes = sorted({r["strike"] for r in rows if r.get("strike") is not None})
    if not strikes:
        return None
    best_strike, best_pain = None, None
    for settlement in strikes:
        pain = 0.0
        for r in rows:
            k = r["strike"]
            oi = r["oi"]
            if r["type"] == "CALL":
                pain += max(settlement - k, 0.0) * oi
            else:
                pain += max(k - settlement, 0.0) * oi
        if best_pain is None or pain < best_pain:
            best_strike, best_pain = settlement, pain
    return best_strike


def analyze_option_chain(symbol="BTCUSD", spot_price=None):
    """Return a live, nearest-expiry option-chain snapshot.

    If Delta's public option endpoint is unavailable, returns a structured
    NO DATA result so the main signal engine can safely fall back to its
    existing technical/astrology/numerology logic.
    """
    underlying = "BTC" if str(symbol).upper() == "BTCUSD" else "ETH"
    try:
        raw = get_option_tickers(underlying)
        if not raw:
            return {"status": "NO DATA", "signal": "NEUTRAL", "reason": "No option tickers returned"}

        today = datetime.now(timezone.utc).date()
        parsed = []
        expiries = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            kind = _kind(item)
            strike = _strike(item)
            expiry = _expiry_from_item(item)
            if kind and strike is not None and expiry and expiry >= today:
                parsed.append((item, kind, strike, expiry))
                expiries.append(expiry)

        if not parsed:
            return {"status": "NO DATA", "signal": "NEUTRAL", "reason": "No current/future option contracts found"}

        expiry = min(expiries)
        rows = []
        for item, kind, strike, exp in parsed:
            if exp != expiry:
                continue
            rows.append({
                "symbol": item.get("symbol"),
                "type": kind,
                "strike": strike,
                "oi": _num(item.get("oi")),
                "volume": _num(item.get("volume")),
                "mark_price": _num(item.get("mark_price")),
                "ltp_change_24h": _num(item.get("ltp_change_24h"), None),
                "iv": _num((item.get("greeks") or {}).get("iv"), None),
            })

        calls = [r for r in rows if r["type"] == "CALL"]
        puts = [r for r in rows if r["type"] == "PUT"]
        call_oi = sum(r["oi"] for r in calls)
        put_oi = sum(r["oi"] for r in puts)
        call_vol = sum(r["volume"] for r in calls)
        put_vol = sum(r["volume"] for r in puts)
        pcr = put_oi / call_oi if call_oi else None
        volume_pcr = put_vol / call_vol if call_vol else None

        spot = _num(spot_price, 0.0)
        if spot <= 0:
            spot = _num(next((r.get("spot_price") for r, *_ in parsed if r.get("spot_price")), 0), 0.0)

        strikes = sorted({r["strike"] for r in rows})
        atm = min(strikes, key=lambda k: abs(k - spot)) if strikes and spot > 0 else None
        call_res = max(calls, key=lambda r: r["oi"], default=None)
        put_sup = max(puts, key=lambda r: r["oi"], default=None)
        max_pain = _max_pain(rows)

        if pcr is None:
            signal = "NEUTRAL"
        elif pcr >= 1.10:
            signal = "BULLISH"
        elif pcr <= 0.90:
            signal = "BEARISH"
        else:
            signal = "SIDEWAYS"

        # Small ATM OI-balance confirmation. It never overrides a strong PCR.
        if atm is not None:
            near = [r for r in rows if abs(r["strike"] - atm) <= (max(abs(atm) * 0.03, 1))]
            near_call = sum(r["oi"] for r in near if r["type"] == "CALL")
            near_put = sum(r["oi"] for r in near if r["type"] == "PUT")
            if signal == "SIDEWAYS" and near_call and near_put:
                ratio = near_put / near_call
                if ratio >= 1.10:
                    signal = "BULLISH"
                elif ratio <= 0.90:
                    signal = "BEARISH"

        top_calls = sorted(calls, key=lambda r: r["oi"], reverse=True)[:5]
        top_puts = sorted(puts, key=lambda r: r["oi"], reverse=True)[:5]

        confidence = 50.0
        if pcr is not None:
            confidence = min(95.0, 50.0 + abs(pcr - 1.0) * 100.0)

        return {
            "status": "OK",
            "signal": signal,
            "confidence": round(confidence, 1),
            "underlying": underlying,
            "expiry": expiry.strftime("%d-%m-%Y"),
            "spot": round(spot, 2) if spot else None,
            "atm_strike": atm,
            "pcr": round(pcr, 4) if pcr is not None else None,
            "volume_pcr": round(volume_pcr, 4) if volume_pcr is not None else None,
            "call_oi": round(call_oi, 2),
            "put_oi": round(put_oi, 2),
            "call_volume": round(call_vol, 2),
            "put_volume": round(put_vol, 2),
            "max_call_oi_resistance": call_res["strike"] if call_res else None,
            "max_put_oi_support": put_sup["strike"] if put_sup else None,
            "max_pain": max_pain,
            "top_call_oi": [{"strike": r["strike"], "oi": r["oi"]} for r in top_calls],
            "top_put_oi": [{"strike": r["strike"], "oi": r["oi"]} for r in top_puts],
            "rows": len(rows),
            "reason": f"PCR {pcr:.2f}" if pcr is not None else "PCR unavailable",
        }
    except Exception as exc:
        return {
            "status": "ERROR",
            "signal": "NEUTRAL",
            "confidence": 0,
            "reason": str(exc),
        }
