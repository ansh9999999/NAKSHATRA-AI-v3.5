"""Kotak Neo v3.0.x market-data adapter for NAKSHATRA.

READ-ONLY market data only. No order-placement calls are made here.
Credentials are read from environment variables; never hard-code secrets.
"""
from __future__ import annotations

import inspect
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from logger import logger

try:
    from neo_api_client import NeoAPI
except Exception as exc:  # package is installed by Render from requirements.txt
    NeoAPI = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

try:
    import pyotp
except Exception:
    pyotp = None

IST = ZoneInfo("Asia/Kolkata")
_CLIENT = None
_CLIENT_LOCK = threading.Lock()
_INSTRUMENT_CACHE = {}

INTERVALS = {
    "1m": "1minute", "3m": "3minute", "5m": "5minute", "10m": "10minute",
    "15m": "15minute", "30m": "30minute", "1h": "60minute", "2h": "120minute",
    "4h": "240minute", "1d": "day",
}


def _env(*names):
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def configured():
    return bool(_env("NEO_CONSUMER_KEY", "KOTAK_CONSUMER_KEY"))


def _client():
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if NeoAPI is None:
        raise RuntimeError(f"kotakneoapi is not installed: {_IMPORT_ERROR}")

    consumer_key = _env("NEO_CONSUMER_KEY", "KOTAK_CONSUMER_KEY")
    if not consumer_key:
        raise RuntimeError("NEO_CONSUMER_KEY is not configured")

    environment = _env("NEO_ENVIRONMENT", "KOTAK_ENVIRONMENT") or "prod"
    access_token = _env("NEO_ACCESS_TOKEN", "KOTAK_ACCESS_TOKEN", "NEO_TOKEN")

    kwargs = {"consumer_key": consumer_key, "environment": environment}
    if access_token:
        kwargs["access_token"] = access_token

    with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = NeoAPI(**kwargs)
            # Optional unattended authentication path. The preferred Render setup
            # is a valid access token; TOTP login is used only when configured.
            _maybe_login(_CLIENT)
    return _CLIENT


def _maybe_login(client):
    if _env("NEO_ACCESS_TOKEN", "KOTAK_ACCESS_TOKEN", "NEO_TOKEN"):
        return
    mobile = _env("NEO_MOBILE_NUMBER", "KOTAK_MOBILE_NUMBER")
    ucc = _env("NEO_UCC", "KOTAK_UCC")
    mpin = _env("NEO_MPIN", "KOTAK_MPIN")
    totp_secret = _env("NEO_TOTP_SECRET", "KOTAK_TOTP_SECRET")
    if not (mobile and ucc and mpin and totp_secret and pyotp):
        return
    code = pyotp.TOTP(totp_secret).now()
    client.totp_login(mobile_number=mobile, ucc=ucc, totp=code)
    client.totp_validate(mpin=mpin)


def _flatten_dicts(value):
    """Yield dictionaries from common Neo response envelopes."""
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from _flatten_dicts(v)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_dicts(item)


def _first(row, *keys):
    for key in keys:
        if key in row and row[key] not in (None, "", "-", "NA"):
            return row[key]
    return None


def _float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def _token_from_row(row):
    value = _first(row, "instrument_token", "pSymbol", "pSymbolToken", "token", "exchange_token")
    return str(value) if value not in (None, "") else None


def _segment_from_row(row, fallback):
    return str(_first(row, "exchange_segment", "pExchSeg", "exchange") or fallback).lower()


def _trading_symbol(row):
    return str(_first(row, "trading_symbol", "pTrdSymbol", "display_symbol", "pScripRefKey", "symbol") or "")


def _parse_expiry(value):
    if value in (None, "", -1, "-1"):
        return None
    if isinstance(value, (int, float)):
        try:
            x = float(value)
            # Neo master may use Unix seconds.
            if x > 1_000_000_000:
                return datetime.fromtimestamp(x, tz=timezone.utc).date()
        except Exception:
            pass
    text = str(value).strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d%b%Y", "%d%b%y", "%d%m%Y", "%d%m%y"):
        try:
            return datetime.strptime(text.upper(), fmt).date()
        except Exception:
            continue
    return None


def find_instrument(symbol):
    """Resolve a registry symbol to a Neo instrument token/segment."""
    from market_registry import get_market, canonical_symbol

    canonical = canonical_symbol(symbol)
    if canonical in _INSTRUMENT_CACHE:
        return _INSTRUMENT_CACHE[canonical]

    market = get_market(canonical)
    if not market or market.get("provider") != "kotak_neo":
        return None

    client = _client()
    segment = market["neo_segment"]
    candidates = market.get("neo_symbols", [canonical])
    rows = []
    for candidate in candidates:
        try:
            result = client.search_scrip(
                exchange_segment=segment,
                symbol=candidate,
                expiry="",
                option_type="",
                strike_price="",
            )
            rows = [r for r in _flatten_dicts(result) if _token_from_row(r)]
            if rows:
                break
        except Exception as exc:
            logger.warning("Neo search_scrip failed %s/%s: %s", canonical, candidate, exc)

    if not rows:
        raise RuntimeError(f"Kotak Neo instrument not found for {canonical} ({segment})")

    # For MCX we prefer the nearest non-expired futures contract. For indices/cash,
    # prefer the first exact/closest symbol returned by the master.
    if segment == "mcx_fo":
        today = datetime.now(IST).date()
        candidates_rows = []
        for row in rows:
            expiry = _parse_expiry(_first(row, "pExpiryDate", "expiry", "expiry_date", "lExpiryDate"))
            if expiry and expiry >= today:
                candidates_rows.append((expiry, row))
        if candidates_rows:
            row = sorted(candidates_rows, key=lambda x: x[0])[0][1]
        else:
            row = rows[0]
    else:
        row = rows[0]

    info = {
        "symbol": canonical,
        "instrument_token": _token_from_row(row),
        "exchange_segment": _segment_from_row(row, segment),
        "trading_symbol": _trading_symbol(row),
        "raw": row,
    }
    _INSTRUMENT_CACHE[canonical] = info
    logger.info("Neo instrument resolved %s -> %s/%s", canonical, info["exchange_segment"], info["instrument_token"])
    return info


def _quote_rows(response):
    rows = []
    for row in _flatten_dicts(response):
        if any(k in row for k in ("ltp", "LTP", "last_price", "last_traded_price", "display_symbol", "exchange_token")):
            rows.append(row)
    return rows


def get_quote(symbol):
    info = find_instrument(symbol)
    client = _client()
    response = client.quotes(
        instrument_tokens=[{
            "instrument_token": info["instrument_token"],
            "exchange_segment": info["exchange_segment"],
        }],
        quote_type="all",
    )
    rows = _quote_rows(response)
    row = rows[0] if rows else next(iter(_flatten_dicts(response)), {})
    ltp = _float(_first(row, "ltp", "LTP", "last_price", "last_traded_price"))
    ohlc = _first(row, "ohlc", "OHLC") or {}
    close = _float(_first(ohlc, "close", "Close", "pClose"), ltp)
    return {
        "symbol": symbol,
        "price": ltp,
        "close": close,
        "mark_price": ltp,
        "volume": _float(_first(row, "last_volume", "volume", "vtt"), 0.0),
        "change": _float(_first(row, "change", "net_change")),
        "change_percent": _float(_first(row, "per_change", "percent_change")),
        "source": "kotak_neo",
        "instrument": info,
        "raw": row,
    }


def _call_by_signature(client, method_name, context):
    method = getattr(client, method_name)
    sig = inspect.signature(method)
    kwargs = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if name in context:
            kwargs[name] = context[name]
    missing = [name for name, p in sig.parameters.items() if name != "self" and p.default is inspect._empty and name not in kwargs]
    if missing:
        raise RuntimeError(f"Kotak Neo {method_name} requires unsupported parameters: {missing}")
    return method(**kwargs)


def _extract_candle_rows(response):
    # Recursively locate lists of dicts that look like candle records.
    candidates = []
    if isinstance(response, list):
        candidates.append(response)
    elif isinstance(response, dict):
        for key in ("data", "candles", "result", "records"):
            value = response.get(key)
            if isinstance(value, list):
                candidates.append(value)
            elif isinstance(value, dict):
                for subkey in ("data", "candles", "records"):
                    if isinstance(value.get(subkey), list):
                        candidates.append(value[subkey])
    for rows in candidates:
        if rows and any(isinstance(x, (dict, list, tuple)) for x in rows):
            return rows
    return []


def _normalize_candles(response):
    rows = _extract_candle_rows(response)
    out = []
    for item in rows:
        if isinstance(item, dict):
            ts = _first(item, "timestamp", "time", "datetime", "date", "t")
            o = _first(item, "open", "Open", "o")
            h = _first(item, "high", "High", "h")
            l = _first(item, "low", "Low", "l")
            c = _first(item, "close", "Close", "c")
            v = _first(item, "volume", "Volume", "v", "vol")
        elif isinstance(item, (list, tuple)) and len(item) >= 5:
            ts, o, h, l, c = item[:5]
            v = item[5] if len(item) > 5 else 0
        else:
            continue
        out.append({"timestamp": ts, "open": _float(o), "high": _float(h), "low": _float(l), "close": _float(c), "volume": _float(v, 0.0)})
    if not out:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(out)
    numeric = ["open", "high", "low", "close", "volume"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    # Numeric epoch fallback.
    bad = ts.isna()
    if bad.any():
        nums = pd.to_numeric(df.loc[bad, "timestamp"], errors="coerce")
        df.loc[bad, "timestamp"] = pd.to_datetime(nums, unit="s", errors="coerce", utc=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df.dropna(subset=["timestamp", "open", "high", "low", "close"], inplace=True)
    df.sort_values("timestamp", inplace=True)
    df.drop_duplicates("timestamp", keep="last", inplace=True)
    return df.set_index("timestamp")[["open", "high", "low", "close", "volume"]]


def get_history(symbol, resolution="5m", limit=200):
    info = find_instrument(symbol)
    client = _client()
    interval = INTERVALS.get(str(resolution).lower().strip(), "5minute")
    try:
        n = max(10, min(int(limit), 2000))
    except Exception:
        n = 200
    seconds = {"1minute": 60, "3minute": 180, "5minute": 300, "10minute": 600, "15minute": 900, "30minute": 1800, "60minute": 3600, "120minute": 7200, "240minute": 14400, "day": 86400}.get(interval, 300)
    end = datetime.now(IST)
    start = end - timedelta(seconds=seconds * n * 1.25)
    context = {
        "exchange_segment": info["exchange_segment"],
        "instrument_token": info["instrument_token"],
        "from_date": start.strftime("%Y-%m-%d %H:%M:%S"),
        "to_date": end.strftime("%Y-%m-%d %H:%M:%S"),
        "start_date": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": end.strftime("%Y-%m-%d %H:%M:%S"),
        "interval": interval,
    }
    response = _call_by_signature(client, "historical_data", context)
    df = _normalize_candles(response)
    if len(df) > n:
        df = df.tail(n)
    return df


def _normalize_option_rows(response):
    rows = []
    for item in _flatten_dicts(response):
        strike = _float(_first(item, "strike_price", "strikePrice", "strike", "dStrikePrice", "pStrikePrice"))
        if strike is None:
            continue
        option_type = str(_first(item, "option_type", "optionType", "pOptionType", "type", "instrument_type") or "").upper()
        if option_type in {"CE", "CALL", "C"}:
            option_type = "CALL"
        elif option_type in {"PE", "PUT", "P"}:
            option_type = "PUT"
        else:
            sym = str(_first(item, "trading_symbol", "pTrdSymbol", "symbol") or "").upper()
            option_type = "CALL" if "CE" in sym else "PUT" if "PE" in sym else ""
        if not option_type:
            continue
        rows.append({
            "symbol": _first(item, "trading_symbol", "pTrdSymbol", "symbol", "display_symbol"),
            "type": option_type,
            "strike": strike,
            "oi": _float(_first(item, "oi", "open_interest", "openInterest", "dOpenInterest"), 0.0),
            "volume": _float(_first(item, "volume", "last_volume", "vtt"), 0.0),
            "ltp": _float(_first(item, "ltp", "last_price", "last_traded_price")),
        })
    # de-duplicate by symbol/strike/type
    seen = set(); clean = []
    for row in rows:
        key = (row.get("symbol"), row["type"], row["strike"])
        if key not in seen:
            seen.add(key); clean.append(row)
    return clean


def get_option_chain(symbol, spot_price=None):
    info = find_instrument(symbol)
    client = _client()
    today = datetime.now(IST).date()
    expiry = ""
    # Prefer a live expiry if the SDK exposes expiries(); signature differences are
    # handled in the same defensive way as historical_data().
    if hasattr(client, "expiries"):
        try:
            response = _call_by_signature(client, "expiries", {
                "exchange_segment": info["exchange_segment"],
                "instrument_token": info["instrument_token"],
                "symbol": info.get("trading_symbol", ""),
            })
            values = []
            for row in _flatten_dicts(response):
                for key in ("expiry", "expiry_date", "pExpiryDate"):
                    d = _parse_expiry(row.get(key))
                    if d and d >= today:
                        values.append(d)
            if values:
                expiry = min(values).strftime("%d-%m-%Y")
        except Exception as exc:
            logger.warning("Neo expiry lookup failed %s: %s", symbol, exc)

    context = {
        "exchange_segment": info["exchange_segment"],
        "instrument_token": info["instrument_token"],
        "underlying_token": info["instrument_token"],
        "scrip_token": info["instrument_token"],
        "expiry": expiry,
    }
    response = _call_by_signature(client, "option_chain", context)
    rows = _normalize_option_rows(response)
    return {"symbol": symbol, "expiry": expiry, "spot": spot_price, "rows": rows, "raw": response}
