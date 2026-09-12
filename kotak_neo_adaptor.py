"""NAKSHATRA AI - Kotak Neo market-data adapter.

Read-only market-data adapter for Indian markets.  It intentionally does not
place, modify or cancel orders.

The adapter uses the current Kotak Neo Python SDK (kotakneoapi / NeoAPI).
Consumer-key-only market-data calls are preferred; TOTP/MPIN are only used
when the SDK endpoint requires an authenticated session.
"""

from __future__ import annotations

import io
import inspect
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests

try:
    from logger import logger
except Exception:  # pragma: no cover
    import logging
    logger = logging.getLogger("nakshatra")


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


CONSUMER_KEY = _env("KOTAK_CONSUMER_KEY", "KOTAK_ACCESS_TOKEN", "NEO_CONSUMER_KEY")
MOBILE_NUMBER = _env("KOTAK_MOBILE_NUMBER", "NEO_MOBILE_NUMBER")
UCC = _env("KOTAK_UCC", "NEO_UCC")
MPIN = _env("KOTAK_MPIN", "NEO_MPIN")
TOTP_SECRET = _env("KOTAK_TOTP_SECRET", "NEO_TOTP_SECRET")

# Optional explicit token mappings.  These make deployment deterministic if
# the user's account has a known token and avoid downloading the scrip master.
_TOKEN_ENV = {
    "NIFTY50": ("KOTAK_NIFTY50_TOKEN", "NEO_NIFTY50_TOKEN"),
    "BANKNIFTY": ("KOTAK_BANKNIFTY_TOKEN", "NEO_BANKNIFTY_TOKEN"),
    "SENSEX": ("KOTAK_SENSEX_TOKEN", "NEO_SENSEX_TOKEN"),
    "NIFTYIT": ("KOTAK_NIFTYIT_TOKEN", "NEO_NIFTYIT_TOKEN"),
    "GOLD": ("KOTAK_GOLD_TOKEN", "NEO_GOLD_TOKEN"),
    "SILVER": ("KOTAK_SILVER_TOKEN", "NEO_SILVER_TOKEN"),
    "CRUDEOIL": ("KOTAK_CRUDEOIL_TOKEN", "NEO_CRUDEOIL_TOKEN"),
}

# Exchange segment used by the read-only quote/historical endpoints.
_SEGMENT = {
    "NIFTY50": "nse_cm",
    "BANKNIFTY": "nse_cm",
    "SENSEX": "bse_cm",
    "NIFTYIT": "nse_cm",
    "GOLD": "mcx_fo",
    "SILVER": "mcx_fo",
    "CRUDEOIL": "mcx_fo",
}

# Common display/scrip-master names.  The resolver also performs fuzzy
# matching, because Kotak's daily scrip-master can change display formatting.
_NAMES = {
    "NIFTY50": ("NIFTY 50", "NIFTY50", "NIFTY"),
    "BANKNIFTY": ("NIFTY BANK", "BANKNIFTY", "NIFTYBANK"),
    "SENSEX": ("SENSEX",),
    "NIFTYIT": ("NIFTY IT", "NIFTYIT", "CNX IT"),
    "GOLD": ("GOLD",),
    "SILVER": ("SILVER",),
    "CRUDEOIL": ("CRUDEOIL", "CRUDE OIL", "CRUDE"),
}


_CLIENT = None
_CLIENT_LOCK = threading.Lock()
_SCRIP_DF: dict[str, pd.DataFrame] = {}
_SCRIP_LOCK = threading.Lock()


def _sdk_client():
    """Create/reuse the current Kotak Neo client."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if not CONSUMER_KEY:
        raise RuntimeError("KOTAK_CONSUMER_KEY is not configured")

    with _CLIENT_LOCK:
        if _CLIENT is not None:
            return _CLIENT
        try:
            from neo_api_client import NeoAPI
        except Exception as exc:
            raise RuntimeError(
                "kotakneoapi is not installed; add kotakneoapi to requirements.txt"
            ) from exc

        _CLIENT = NeoAPI(consumer_key=CONSUMER_KEY, environment="prod")
        return _CLIENT


def _maybe_auth(client) -> None:
    """Authenticate only if all required values are available.

    Current Kotak market-data quotes/scrip-master endpoints can work with the
    consumer key alone.  Historical/option endpoints may require a session on
    some account/API configurations, so authenticate lazily when credentials
    are available.
    """
    if not (MOBILE_NUMBER and UCC and MPIN):
        return

    # Avoid repeated login if the SDK exposes a session/auth marker.
    for attr in ("access_token", "session_token", "sessionToken"):
        if getattr(client, attr, None):
            return

    # If no TOTP secret is available, don't invent a code.  Quotes can still
    # be used with consumer-key authentication.
    if not TOTP_SECRET:
        return

    try:
        import pyotp
        totp = pyotp.TOTP(TOTP_SECRET).now()
        client.totp_login(mobile_number=MOBILE_NUMBER, ucc=UCC, totp=totp)
        client.totp_validate(mpin=MPIN)
    except Exception as exc:
        logger.warning("Kotak Neo optional session authentication failed: %s", exc)


def _clean_symbol(symbol: str) -> str:
    s = str(symbol or "").strip().upper()
    aliases = {
        "NIFTY": "NIFTY50",
        "NIFTY 50": "NIFTY50",
        "NIFTY50": "NIFTY50",
        "BANK NIFTY": "BANKNIFTY",
        "NIFTY BANK": "BANKNIFTY",
        "BANKNIFTY": "BANKNIFTY",
        "SENSEX": "SENSEX",
        "NIFTY IT": "NIFTYIT",
        "CNXIT": "NIFTYIT",
        "NIFTYIT": "NIFTYIT",
        "GOLD": "GOLD",
        "SILVER": "SILVER",
        "CRUDE": "CRUDEOIL",
        "CRUDE OIL": "CRUDEOIL",
        "CRUDEOIL": "CRUDEOIL",
    }
    return aliases.get(s, s)


def _token_from_env(symbol: str) -> str:
    for name in _TOKEN_ENV.get(symbol, ()):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _find_col(df: pd.DataFrame, *wanted: str) -> str | None:
    normalized = {re.sub(r"[^a-z0-9]", "", str(c).lower()): c for c in df.columns}
    for w in wanted:
        key = re.sub(r"[^a-z0-9]", "", w.lower())
        if key in normalized:
            return normalized[key]
    return None


def _scrip_master(symbol: str) -> pd.DataFrame:
    segment = _SEGMENT[symbol]
    with _SCRIP_LOCK:
        if segment in _SCRIP_DF:
            return _SCRIP_DF[segment]

    client = _sdk_client()
    response = client.scrip_master(exchange_segment=segment)
    url = None
    if isinstance(response, str):
        url = response
    elif isinstance(response, dict):
        # New SDK returns a list of exact daily file paths.
        paths = response.get("filesPaths") or response.get("files_paths") or []
        base = response.get("baseFolder", "")
        candidates = [p for p in paths if segment in str(p).lower()]
        if candidates:
            url = candidates[0]
        elif base:
            url = str(base).rstrip("/") + "/" + segment + ".csv"

    if not url:
        raise RuntimeError(f"Kotak scrip master URL unavailable for {segment}")

    r = requests.get(url, timeout=30, headers={"User-Agent": "NAKSHATRA-AI/5.0"})
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content), low_memory=False)
    with _SCRIP_LOCK:
        _SCRIP_DF[segment] = df
    return df


def _resolve_instrument(symbol: str) -> tuple[str, str]:
    """Return (exchange_segment, instrument_token)."""
    symbol = _clean_symbol(symbol)
    segment = _SEGMENT.get(symbol)
    if not segment:
        raise ValueError(f"Unsupported Kotak Neo symbol: {symbol}")

    explicit = _token_from_env(symbol)
    if explicit:
        return segment, explicit

    df = _scrip_master(symbol)
    name_col = _find_col(
        df, "display_symbol", "symbol", "trading_symbol", "pSymbol", "pTrdSymbol", "symbol_name"
    )
    token_col = _find_col(
        df, "instrument_token", "token", "pSymbolToken", "pScripCode", "exchange_token"
    )
    if not name_col or not token_col:
        raise RuntimeError(
            f"Kotak scrip master columns not recognised for {symbol}: {list(df.columns)[:20]}"
        )

    names = [re.sub(r"[^A-Z0-9]", "", n.upper()) for n in _NAMES[symbol]]
    values = df[name_col].astype(str).str.upper().map(lambda x: re.sub(r"[^A-Z0-9]", "", x))

    # Prefer exact matches, then contains matches.
    for target in names:
        exact = df[values == target]
        if not exact.empty:
            return segment, str(exact.iloc[0][token_col])
    for target in names:
        hit = df[values.str.contains(target, regex=False, na=False)]
        if not hit.empty:
            return segment, str(hit.iloc[0][token_col])

    raise RuntimeError(f"Kotak instrument token not found for {symbol}")


def _extract_list(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "Data", "result", "results", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = _extract_list(value)
                if nested:
                    return nested
    return []


def _call_with_variants(fn, variants: list[dict[str, Any]]):
    """Call an SDK method against known v3 signature variants."""
    last_type_error = None
    for kwargs in variants:
        try:
            return fn(**kwargs)
        except TypeError as exc:
            last_type_error = exc
            continue
    if last_type_error:
        raise last_type_error
    raise RuntimeError("No valid SDK call variant")


def _normalise_candles(payload: Any) -> pd.DataFrame:
    rows = _extract_list(payload)
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"],
                            index=pd.DatetimeIndex([], name="timestamp"))

    # Some broker responses use lists in fixed OHLCV order.
    if rows and isinstance(rows[0], (list, tuple)):
        rows = [
            {
                "timestamp": r[0] if len(r) > 0 else None,
                "open": r[1] if len(r) > 1 else None,
                "high": r[2] if len(r) > 2 else None,
                "low": r[3] if len(r) > 3 else None,
                "close": r[4] if len(r) > 4 else None,
                "volume": r[5] if len(r) > 5 else 0,
            }
            for r in rows
        ]

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    def col(*names):
        return _find_col(df, *names)

    t = col("timestamp", "time", "datetime", "date", "timeStamp")
    o = col("open", "openPrice", "o")
    h = col("high", "highPrice", "h")
    l = col("low", "lowPrice", "l")
    c = col("close", "closePrice", "c")
    v = col("volume", "vol", "v")
    if not all((t, o, h, l, c)):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"],
                            index=pd.DatetimeIndex([], name="timestamp"))

    out = pd.DataFrame({
        "timestamp": df[t],
        "open": pd.to_numeric(df[o], errors="coerce"),
        "high": pd.to_numeric(df[h], errors="coerce"),
        "low": pd.to_numeric(df[l], errors="coerce"),
        "close": pd.to_numeric(df[c], errors="coerce"),
        "volume": pd.to_numeric(df[v], errors="coerce") if v else 0.0,
    })
    # Handle unix seconds/milliseconds and normal date strings.
    numeric_t = pd.to_numeric(out["timestamp"], errors="coerce")
    if numeric_t.notna().mean() > 0.8:
        sample = float(numeric_t.dropna().iloc[0])
        unit = "s"
        if abs(sample) > 10_000_000_000_000:
            unit = "us"
        elif abs(sample) > 10_000_000_000:
            unit = "ms"
        out["timestamp"] = pd.to_datetime(numeric_t, unit=unit, utc=True, errors="coerce")
    else:
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")

    out.dropna(subset=["timestamp", "open", "high", "low", "close"], inplace=True)
    out.sort_values("timestamp", inplace=True)
    out.set_index("timestamp", inplace=True)
    return out[["open", "high", "low", "close", "volume"]]


def _interval(resolution: str) -> str:
    r = str(resolution).lower().strip()
    return {"1m": "1minute", "3m": "3minute", "5m": "5minute",
            "15m": "15minute", "30m": "30minute", "1h": "60minute",
            "2h": "120minute", "4h": "240minute", "1d": "day",
            "1w": "week"}.get(r, "5minute")


def get_history(symbol: str = "NIFTY50", resolution: str = "5m", limit: int = 200) -> pd.DataFrame:
    """Fetch historical OHLCV candles for an Indian market symbol."""
    symbol = _clean_symbol(symbol)
    if symbol not in _SEGMENT:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"],
                            index=pd.DatetimeIndex([], name="timestamp"))

    try:
        client = _sdk_client()
        _maybe_auth(client)
        segment, token = _resolve_instrument(symbol)
        fn = getattr(client, "historical_data")

        # Use a conservative recent window.  Kotak's endpoint accepts dates;
        # the exact argument names changed during the v2 -> v3 migration, so
        # support both documented variants without coupling NAKSHATRA to one
        # minor SDK release.
        days = max(2, min(60, int(limit * 5 / 78) + 2))
        to_dt = datetime.now(timezone.utc)
        from_dt = to_dt - timedelta(days=days)
        date1 = from_dt.strftime("%d/%m/%Y")
        date2 = to_dt.strftime("%d/%m/%Y")

        variants = [
            {"exchange_segment": segment, "instrument_token": token, "from_date": date1,
             "to_date": date2, "interval": _interval(resolution)},
            {"exchange_segment": segment, "instrument_token": token, "from_date": from_dt.strftime("%Y-%m-%d"),
             "to_date": to_dt.strftime("%Y-%m-%d"), "interval": _interval(resolution)},
            {"exchange_segment": segment, "instrument_token": token, "from_date": date1,
             "to_date": date2, "interval": str(resolution).lower()},
        ]
        payload = _call_with_variants(fn, variants)
        df = _normalise_candles(payload)
        if not df.empty:
            return df.tail(max(10, int(limit)))
        logger.warning("No Kotak Neo candle data for %s %s", symbol, resolution)
    except Exception as exc:
        logger.warning("Kotak Neo history failed for %s %s: %s", symbol, resolution, exc)
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"],
                        index=pd.DatetimeIndex([], name="timestamp"))


def get_multi_timeframe_history(symbol: str = "NIFTY50", limit: int = 200):
    symbol = _clean_symbol(symbol)
    return {
        "symbol": symbol,
        "5m": get_history(symbol, "5m", limit),
        "15m": get_history(symbol, "15m", limit),
        "1h": get_history(symbol, "1h", limit),
        "1d": get_history(symbol, "1d", limit),
    }


def get_quote(symbol: str = "NIFTY50") -> dict[str, Any]:
    """Return a normalised live quote dictionary."""
    symbol = _clean_symbol(symbol)
    try:
        client = _sdk_client()
        segment, token = _resolve_instrument(symbol)
        response = client.quotes(
            instrument_tokens=[{"instrument_token": str(token), "exchange_segment": segment}],
            quote_type="all",
        )
        rows = _extract_list(response)
        item = rows[0] if rows else (response[0] if isinstance(response, list) and response else {})
        if not isinstance(item, dict):
            return {"status": "NO DATA", "symbol": symbol}
        ohlc = item.get("ohlc") or {}
        return {
            "status": "OK",
            "symbol": symbol,
            "instrument_token": str(token),
            "exchange_segment": segment,
            "ltp": float(item.get("ltp", 0) or 0),
            "open": float(ohlc.get("open", 0) or 0),
            "high": float(ohlc.get("high", 0) or 0),
            "low": float(ohlc.get("low", 0) or 0),
            "close": float(ohlc.get("close", 0) or 0),
            "volume": float(item.get("last_volume", 0) or 0),
            "oi": float(item.get("open_int", 0) or 0),
            "change": float(item.get("change", 0) or 0),
            "per_change": float(item.get("per_change", 0) or 0),
            "raw": item,
        }
    except Exception as exc:
        logger.warning("Kotak Neo quote failed for %s: %s", symbol, exc)
        return {"status": "ERROR", "symbol": symbol, "reason": str(exc)}


def get_option_chain(symbol: str = "NIFTY50", expiry: str | None = None) -> list[dict[str, Any]]:
    """Return normalized option-chain rows using Kotak Neo SDK v3.x.

    Kotak Neo v3.x option_chain() is an underlying-based market-data endpoint:
        client.option_chain(exchange, underlying, expiry=None,
                            instrument_type="option", count=40)

    It does NOT require an index cash-market token or the scrip-master
    resolver.  The previous implementation incorrectly tried to resolve the
    underlying through the cash-market scrip master and then passed the wrong
    keyword arguments to option_chain().
    """
    symbol = _clean_symbol(symbol)

    meta = {
        "NIFTY50": ("nse_fo", "NIFTY"),
        "BANKNIFTY": ("nse_fo", "BANKNIFTY"),
        "SENSEX": ("bse_fo", "SENSEX"),
        "NIFTYIT": ("nse_fo", "NIFTYIT"),
    }
    if symbol not in meta:
        return []

    exchange, underlying = meta[symbol]

    try:
        client = _sdk_client()
        # option_chain() is consumer-key authenticated market data and does
        # not require a completed TOTP session according to the v3.x SDK.
        fn = getattr(client, "option_chain", None)
        if not callable(fn):
            raise RuntimeError("Installed Kotak Neo SDK has no option_chain().")

        kwargs = {
            "exchange": exchange,
            "underlying": underlying,
            "instrument_type": "option",
            "count": 40,
        }
        if expiry:
            kwargs["expiry"] = str(expiry)

        payload = fn(**kwargs)

        if not isinstance(payload, dict):
            logger.warning("Kotak Neo option chain returned unexpected type for %s: %s", symbol, type(payload).__name__)
            return []

        data = payload.get("data")
        if not isinstance(data, dict):
            data = payload.get("result") if isinstance(payload.get("result"), dict) else {}

        common = data.get("common_data") or data.get("commonData") or {}
        chain_expiry = common.get("expiryDt") or common.get("expiry") or expiry

        rows: list[dict[str, Any]] = []

        for side, option_type in (("call", "CALL"), ("put", "PUT")):
            items = data.get(side) or []
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue

                instrument = item.get("instrument") or item.get("inst") or {}
                quote = item.get("quote") or {}
                oi_data = item.get("openInterest") or item.get("oi") or {}

                strike = (
                    instrument.get("strikePrice")
                    if isinstance(instrument, dict)
                    else None
                )
                if strike in (None, ""):
                    strike = item.get("strike_price", item.get("strike"))

                oi = (
                    oi_data.get("current")
                    if isinstance(oi_data, dict)
                    else oi_data
                )
                volume = (
                    quote.get("volume")
                    if isinstance(quote, dict)
                    else 0
                )
                ltp = (
                    quote.get("ltp")
                    if isinstance(quote, dict)
                    else 0
                )

                try:
                    strike_value = float(strike)
                except Exception:
                    continue

                try:
                    oi_value = float(oi or 0)
                except Exception:
                    oi_value = 0.0

                try:
                    volume_value = float(volume or 0)
                except Exception:
                    volume_value = 0.0

                try:
                    ltp_value = float(ltp or 0)
                except Exception:
                    ltp_value = 0.0

                trading_symbol = (
                    instrument.get("symbol")
                    if isinstance(instrument, dict)
                    else None
                ) or item.get("trading_symbol") or item.get("symbol")

                rows.append({
                    "symbol": trading_symbol,
                    "type": option_type,
                    "strike": strike_value,
                    "oi": oi_value,
                    "volume": volume_value,
                    "ltp": ltp_value,
                    "expiry": chain_expiry,
                    "raw": item,
                })

        rows.sort(key=lambda r: (float(r["strike"]), 0 if r["type"] == "CALL" else 1))
        logger.info(
            "KOTAK OPTION CHAIN OK %s exchange=%s underlying=%s expiry=%s rows=%s",
            symbol, exchange, underlying, chain_expiry, len(rows)
        )
        return rows

    except Exception as exc:
        logger.warning("Kotak Neo option chain failed for %s: %s", symbol, exc)
        return []

