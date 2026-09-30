"""Intraday market-regime/shift detector.

Uses already available historical candles; it does not invent a live event time.
The detector compares the latest completed 5m/15m state with recent bars and
returns a shift only when multiple independent conditions agree.
"""
from __future__ import annotations

import time
import threading
import pandas as pd

from history import get_multi_timeframe_history
from market_registry import canonical_symbol

_LOCK = threading.Lock()
_CACHE = {}
_TTL = 15.0


def _num(v):
    try:
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


def _rsi(c, period=14):
    d = c.diff()
    up = d.clip(lower=0)
    down = -d.clip(upper=0)
    au = up.ewm(alpha=1/period, adjust=False).mean()
    ad = down.ewm(alpha=1/period, adjust=False).mean()
    rs = au / ad.replace(0, float("nan"))
    r = 100 - (100 / (1 + rs))
    return r.fillna(50)


def _state(df):
    if df is None or df.empty or "close" not in df.columns or len(df) < 25:
        return None
    x = df.copy().reset_index(drop=True)
    c = pd.to_numeric(x["close"], errors="coerce")
    c = c.dropna()
    if len(c) < 25:
        return None
    e9 = c.ewm(span=9, adjust=False).mean()
    e21 = c.ewm(span=21, adjust=False).mean()
    e50 = c.ewm(span=50, adjust=False).mean()
    r = _rsi(c)
    i = len(c) - 1
    price = float(c.iloc[i])
    prev5 = float(c.iloc[i-1])
    prev3 = float(c.iloc[max(0, i-3)])
    ret1 = (price / prev5 - 1) * 100 if prev5 else 0
    ret3 = (price / prev3 - 1) * 100 if prev3 else 0
    volume = None
    rvol = None
    if "volume" in x.columns:
        v = pd.to_numeric(x["volume"], errors="coerce").dropna()
        if len(v) >= 21:
            volume = float(v.iloc[-1])
            avg = float(v.iloc[-21:-1].mean())
            if avg > 0:
                rvol = volume / avg
    score = 0
    reasons = []
    if price < float(e9.iloc[i]): score -= 18; reasons.append("Price below EMA9")
    else: score += 18; reasons.append("Price above EMA9")
    if float(e9.iloc[i]) < float(e21.iloc[i]): score -= 16; reasons.append("EMA9 below EMA21")
    else: score += 16; reasons.append("EMA9 above EMA21")
    if i >= 3:
        e9_slope = float(e9.iloc[i] - e9.iloc[i-3])
        if e9_slope < 0: score -= 12; reasons.append("EMA9 slope falling")
        elif e9_slope > 0: score += 12; reasons.append("EMA9 slope rising")
    if float(r.iloc[i]) < 40: score -= 15; reasons.append(f"RSI below 40 ({float(r.iloc[i]):.1f})")
    elif float(r.iloc[i]) > 60: score += 15; reasons.append(f"RSI above 60 ({float(r.iloc[i]):.1f})")
    if ret3 < -0.20: score -= 18; reasons.append(f"3-bar momentum {ret3:.2f}%")
    elif ret3 > 0.20: score += 18; reasons.append(f"3-bar momentum +{ret3:.2f}%")
    if rvol is not None and rvol >= 1.5:
        if ret1 < 0: score -= 10; reasons.append(f"High-volume sell impulse RVOL {rvol:.1f}")
        elif ret1 > 0: score += 10; reasons.append(f"High-volume buy impulse RVOL {rvol:.1f}")
    score = max(-100, min(100, score))
    bias = "BULLISH" if score >= 35 else "BEARISH" if score <= -35 else "NEUTRAL"
    return {
        "price": price, "ema9": float(e9.iloc[i]), "ema21": float(e21.iloc[i]),
        "ema50": float(e50.iloc[i]), "rsi": float(r.iloc[i]), "return_1bar": ret1,
        "return_3bar": ret3, "volume": volume, "rvol": rvol, "score": score,
        "bias": bias, "reasons": reasons,
    }


def _timestamp(df):
    if df is None or df.empty:
        return None
    try:
        idx = df.index[-1]
        if hasattr(idx, "isoformat"):
            return idx.isoformat()
        if "timestamp" in df.columns:
            return str(df.iloc[-1]["timestamp"])
    except Exception:
        pass
    return None


def detect_market_shift(symbol: str):
    symbol = canonical_symbol(symbol)
    now = time.time()
    with _LOCK:
        c = _CACHE.get(symbol)
        if c and now - c[0] < _TTL:
            return c[1]
    try:
        data = get_multi_timeframe_history(symbol, limit=220)
        s5 = _state(data.get("5m"))
        s15 = _state(data.get("15m"))
        if not s5:
            out = {"status":"NO DATA","symbol":symbol,"bias":"WAIT","strength":0,"phase":"NO DATA","action":"WAIT","note":"5m candle history unavailable."}
        else:
            # Shift is about a change in regime, not merely the current trend.
            prev_df = data.get("5m")
            prev_state = None
            if prev_df is not None and len(prev_df) >= 26:
                prev_state = _state(prev_df.iloc[:-1].copy())
            delta = (s5["score"] - prev_state["score"]) if prev_state else 0
            bearish_trigger = s5["score"] <= -55 and delta <= -15
            bullish_trigger = s5["score"] >= 55 and delta >= 15
            confirm15_bear = bool(s15 and s15["score"] <= -25)
            confirm15_bull = bool(s15 and s15["score"] >= 25)
            if bearish_trigger:
                bias = "BEARISH"; phase = "CONFIRMED" if confirm15_bear else "SHIFTING"; action = "PE BUY WATCH" if confirm15_bear else "WAIT FOR 15M CONFIRMATION"
            elif bullish_trigger:
                bias = "BULLISH"; phase = "CONFIRMED" if confirm15_bull else "SHIFTING"; action = "CE BUY WATCH" if confirm15_bull else "WAIT FOR 15M CONFIRMATION"
            else:
                bias = s5["bias"]
                phase = "TRENDING" if abs(s5["score"]) >= 35 else "SIDEWAYS"
                action = "PE BUY WATCH" if bias == "BEARISH" and confirm15_bear else "CE BUY WATCH" if bias == "BULLISH" and confirm15_bull else "WAIT"
            strength = min(100, abs(int(s5["score"])))
            out = {
                "status":"OK", "symbol":symbol, "bias":bias, "strength":strength,
                "phase":phase, "action":action, "score_5m":s5["score"],
                "previous_score_5m":prev_state["score"] if prev_state else None,
                "score_change":delta, "current_5m":s5, "confirm_15m":s15,
                "detected_candle":_timestamp(data.get("5m")),
                "note":"Market shift is detected from 5m momentum/EMA/RSI/volume and checked against 15m confirmation. It is not dealer/FII live positioning.",
            }
            if prev_state and ((s5["bias"] != prev_state["bias"]) or abs(delta) >= 25):
                out["shift_detected"] = True
                out["shift_type"] = f"{prev_state['bias']} → {s5['bias']}"
            else:
                out["shift_detected"] = False
                out["shift_type"] = "NO NEW REGIME SHIFT"
        with _LOCK:
            _CACHE[symbol] = (now, out)
        return out
    except Exception as exc:
        out = {"status":"ERROR","symbol":symbol,"bias":"WAIT","strength":0,"phase":"ERROR","action":"WAIT","error":str(exc)}
        with _LOCK:
            _CACHE[symbol] = (now, out)
        return out
