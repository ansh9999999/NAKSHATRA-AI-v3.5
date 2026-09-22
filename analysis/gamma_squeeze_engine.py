"""Simple, conservative option squeeze / gamma-risk detector.

This module is intentionally independent of broker APIs. It consumes normalized
option-chain rows and returns a small, explainable alert used by the dashboard.
It never invents an exact blast time and returns WAIT when the live chain is
insufficient.
"""
from datetime import datetime
import math


def _n(v, default=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _window():
    # A rolling watch window is deliberately broad; exact timing is not
    # inferable from an option chain snapshot alone.
    h = datetime.now().hour
    if h < 10:
        return "10:00–11:00 IST"
    if h < 12:
        return "Next 60 min"
    if h < 14:
        return "Next 60 min"
    if h < 15:
        return "Next 30–60 min"
    return "Next session / no live trigger"


def detect_squeeze(symbol, rows, spot, expiry=None):
    rows = rows or []
    calls = [r for r in rows if str(r.get("type", "")).upper() == "CALL"]
    puts = [r for r in rows if str(r.get("type", "")).upper() == "PUT"]
    spot = _n(spot)

    if not calls or not puts or spot <= 0:
        return {
            "status": "NO DATA", "risk": "NO DATA", "side": "NO CLEAR SIDE",
            "confirmations": 0, "confirmation_total": 5,
            "probable_window": "—", "trigger": "Live CE/PE option-chain data required.",
            "reason": "Insufficient live option-chain data.",
            "warning": "No squeeze signal without live chain confirmation.",
            "expiry_day": False,
        }

    strikes = sorted({_n(r.get("strike")) for r in rows if _n(r.get("strike")) > 0})
    atm = min(strikes, key=lambda x: abs(x - spot)) if strikes else None
    if atm is None:
        return {"status":"NO DATA","risk":"NO DATA","side":"NO CLEAR SIDE","confirmations":0,"confirmation_total":5,"probable_window":"—","trigger":"ATM strike unavailable.","reason":"No valid strikes.","warning":"Wait for valid option-chain data.","expiry_day":False}

    band = max(abs(atm) * 0.01, 100 if atm > 10000 else 25)
    near_c = [r for r in calls if abs(_n(r.get("strike")) - atm) <= band]
    near_p = [r for r in puts if abs(_n(r.get("strike")) - atm) <= band]

    def oi(rows): return sum(_n(r.get("oi")) for r in rows)
    def vol(rows): return sum(_n(r.get("volume")) for r in rows)
    def doi(rows): return sum(_n(r.get("oi_change")) for r in rows)

    coi, poi = oi(near_c), oi(near_p)
    cdoi, pdoi = doi(near_c), doi(near_p)
    cvol, pvol = vol(near_c), vol(near_p)

    # Conservative setup confirmation: OI unwinding + volume dominance + spot
    # proximity. A direction is only shown when the chain itself provides a
    # coherent unwind signature.
    call_unwind = coi > 0 and cdoi < -0.05 * coi
    put_unwind = poi > 0 and pdoi < -0.05 * poi
    call_vol = cvol > 0 and cvol >= pvol * 1.15
    put_vol = pvol > 0 and pvol >= cvol * 1.15

    side = "NO CLEAR SIDE"
    confirmations = 0
    if call_unwind:
        confirmations += 1
    if put_unwind:
        confirmations += 1

    if call_unwind and call_vol and not put_unwind:
        side = "CALL"
        confirmations = min(5, 3 + int(cvol > pvol * 1.5))
    elif put_unwind and put_vol and not call_unwind:
        side = "PUT"
        confirmations = min(5, 3 + int(pvol > cvol * 1.5))
    elif call_unwind and put_unwind:
        side = "BOTH-WHIPSAW"
        confirmations = 2

    # Expiry day: compare date portion when supplied in common formats.
    expiry_day = False
    if expiry:
        text = str(expiry)
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y"):
            try:
                expiry_day = datetime.now().date() == datetime.strptime(text[:10], fmt).date()
                break
            except Exception:
                pass

    risk = "HIGH" if confirmations >= 4 and side in ("CALL", "PUT") else "ELEVATED" if confirmations >= 3 and side in ("CALL", "PUT") else "WATCH" if confirmations >= 2 else "LOW"
    if side == "NO CLEAR SIDE":
        risk = "LOW"

    if side == "CALL":
        trigger = "NIFTY sustains above ATM + nearby CE OI unwinds + CE volume expands."
        reason = "Nearby CE OI unwinding with stronger CE activity."
    elif side == "PUT":
        trigger = "NIFTY sustains below ATM + nearby PE OI unwinds + PE volume expands."
        reason = "Nearby PE OI unwinding with stronger PE activity."
    elif side == "BOTH-WHIPSAW":
        trigger = "No trade until one side clearly dominates."
        reason = "CE and PE OI are both unwinding; whipsaw risk is elevated."
    else:
        trigger = "Wait for clear CE or PE OI unwinding with volume confirmation."
        reason = "No confirmed squeeze signature yet."

    return {
        "status": "OK", "risk": risk, "side": side,
        "confirmations": confirmations, "confirmation_total": 5,
        "probable_window": _window(), "trigger": trigger,
        "reason": reason,
        "warning": "Probable window only; wait for the live trigger. Exact blast time is not predictable.",
        "expiry_day": expiry_day,
        "atm": atm,
    }
