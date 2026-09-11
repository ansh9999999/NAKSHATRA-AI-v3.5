"""
NAKSHATRA AI - Kotak Neo market-data adapter.

Purpose:
- Indian live quotes
- Indian historical candles
- NSE/BSE indices
- MCX front-contract discovery

No order placement is implemented here. NAKSHATRA remains manual-only.

The adapter is deliberately defensive because Kotak Neo's scrip-master
response can change shape between SDK releases.
"""

from __future__ import annotations

import inspect
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from config import (
    KOTAK_ACCESS_TOKEN,
    KOTAK_CONSUMER_KEY,
    KOTAK_ENVIRONMENT,
    KOTAK_MOBILE_NUMBER,
    KOTAK_MPIN,
    KOTAK_NEO_FIN_KEY,
    KOTAK_TOTP_SECRET,
    KOTAK_UCC,
)
from logger import logger
from market_registry import canonical_symbol, get_market

try:
    from neo_api_client import NeoAPI
except Exception as exc:  # pragma: no cover
    NeoAPI = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


_CLIENT = None
_CLIENT_LOCK = threading.Lock()
_TOKEN_CACHE: dict[str, dict[str, Any]] = {}
_TOKEN_TTL = 6 * 60 * 60


def _require_sdk():
    if NeoAPI is None:
        raise RuntimeError(
            "Kotak Neo SDK is not installed. Add kotakneoapi to requirements.txt."
        ) from _IMPORT_ERROR


def _make_client():
    _require_sdk()

    kwargs = {
        "consumer_key": KOTAK_CONSUMER_KEY,
        "environment": KOTAK_ENVIRONMENT or "prod",
    }

    # Access token is optional. Keep it if the user has one configured.
    if KOTAK_ACCESS_TOKEN:
        kwargs["access_token"] = KOTAK_ACCESS_TOKEN

    if KOTAK_NEO_FIN_KEY:
        kwargs["neo_fin_key"] = KOTAK_NEO_FIN_KEY

    return NeoAPI(**kwargs)


def _client():
    global _CLIENT
    if not KOTAK_CONSUMER_KEY:
        raise RuntimeError("KOTAK_CONSUMER_KEY is missing in Render Environment.")

    with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = _make_client()
        return _CLIENT


def _maybe_authenticate():
    """
    Authenticate only when enough unattended-auth material exists.

    Quotes and scrip-master are intentionally usable with the consumer key
    alone. Historical/derivative endpoints may require an authenticated
    session depending on the Kotak API endpoint/account.
    """
    client = _client()

    # If an access token was supplied, don't force a new TOTP session.
    if KOTAK_ACCESS_TOKEN:
        return client

    if not (KOTAK_TOTP_SECRET and KOTAK_MOBILE_NUMBER and KOTAK_UCC and KOTAK_MPIN):
        return client

    try:
        import pyotp

        totp = pyotp.TOTP(KOTAK_TOTP_SECRET).now()
        client.totp_login(
            mobile_number=KOTAK_MOBILE_NUMBER,
            ucc=KOTAK_UCC,
            totp=totp,
        )
        client.totp_validate(mpin=KOTAK_MPIN)
        logger.info("KOTAK NEO authentication successful")
    except Exception as exc:
        logger.warning("KOTAK NEO authentication unavailable: %s", exc)

    return client


def _walk_objects(value):
    """Yield dictionaries/lists recursively from arbitrary SDK responses."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_objects(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_objects(child)


def _text(value):
    return str(value or "").strip()


def _first(record: dict, *keys):
    lower = {str(k).lower(): v for k, v in record.items()}
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
        if key.lower() in lower and lower[key.lower()] not in (None, ""):
            return lower[key.lower()]
    return None


def _normalise_record(record: dict) -> dict:
    return {
        "instrument_token": _first(
            record,
            "instrument_token",
            "instrumentToken",
            "token",
            "exchange_token",
            "exchangeToken",
            "scrip_token",
            "scripToken",
            "pSymbol",
            "pScripCode",
        ),
        "exchange_segment": _first(
            record,
            "exchange_segment",
            "exchangeSegment",
            "exchange",
            "pExchSeg",
        ),
        "trading_symbol": _first(
            record,
            "trading_symbol",
            "tradingSymbol",
            "display_symbol",
            "displaySymbol",
            "pTrdSymbol",
            "symbol",
            "name",
        ),
        "expiry": _first(
            record,
            "expiry",
            "expiryDate",
            "pExpiryDate",
            "pExpiry",
        ),
        "instrument_type": _first(
            record,
            "instrument_type",
            "instrumentType",
            "pInstType",
        ),
    }


def _looks_like_symbol(record: dict, candidates: list[str]) -> bool:
    values = [
        _text(_first(record, "trading_symbol", "tradingSymbol", "display_symbol")),
        _text(_first(record, "symbol", "name")),
    ]
    wanted = [re.sub(r"[^A-Z0-9]", "", x.upper()) for x in candidates]

    for value in values:
        normal = re.sub(r"[^A-Z0-9]", "", value.upper())
        for w in wanted:
            if normal == w or normal.startswith(w):
                return True
    return False


def _extract_search_records(response):
    records = []
    for obj in _walk_objects(response):
        # Avoid treating every nested dictionary as a scrip.
        token = _first(
            obj,
            "instrument_token",
            "instrumentToken",
            "exchange_token",
            "exchangeToken",
            "scrip_token",
            "scripToken",
            "pSymbol",
            "pScripCode",
        )
        symbol = _first(
            obj,
            "trading_symbol",
            "tradingSymbol",
            "display_symbol",
            "displaySymbol",
            "pTrdSymbol",
            "symbol",
            "name",
        )
        if token is not None and symbol is not None:
            records.append(_normalise_record(obj))
    return records


def _search_scrip(market):
    client = _client()
    segment = market["neo_exchange_segment"]
    candidates = market.get("neo_symbol_candidates", [])

    search = getattr(client, "search_scrip", None)
    if callable(search):
        for candidate in candidates:
            attempts = [
                {
                    "exchange_segment": segment,
                    "symbol": candidate,
                    "expiry": "",
                    "option_type": "FUT" if segment == "mcx_fo" else "",
                    "strike_price": "",
                },
                {
                    "exchange_segment": segment,
                    "symbol": candidate,
                },
            ]
            for kwargs in attempts:
                try:
                    response = search(**kwargs)
                    records = _extract_search_records(response)
                    if records:
                        return _choose_record(records, market)
                except TypeError:
                    continue
                except Exception as exc:
                    logger.debug("KOTAK search_scrip failed %s: %s", candidate, exc)

    # Last resort: use scrip_master and download the relevant segment file.
    return _search_scrip_master(client, market)


def _search_scrip_master(client, market):
    segment = market["neo_exchange_segment"]
    candidates = market.get("neo_symbol_candidates", [])

    fn = getattr(client, "scrip_master", None)
    if not callable(fn):
        return None

    try:
        response = fn(exchange_segment=segment)
    except TypeError:
        response = fn()

    urls = []
    if isinstance(response, str):
        urls = [response]
    else:
        for obj in _walk_objects(response):
            for key in ("filePath", "file_path", "url", "path"):
                value = obj.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    urls.append(value)
            for key in ("filesPaths", "filePaths"):
                value = obj.get(key)
                if isinstance(value, list):
                    urls.extend(str(x) for x in value if str(x).startswith("http"))

    urls = list(dict.fromkeys(urls))
    if not urls:
        return None

    for url in urls:
        try:
            df = pd.read_csv(url, low_memory=False)
            if df.empty:
                continue

            records = []
            for _, row in df.iterrows():
                rec = {str(k): row[k] for k in df.columns}
                normal = _normalise_record(rec)
                if normal["instrument_token"] is None:
                    continue
                if _looks_like_symbol(rec, candidates):
                    records.append(normal)

            if records:
                return _choose_record(records, market)
        except Exception as exc:
            logger.warning("KOTAK scrip master read failed: %s", exc)

    return None


def _expiry_key(value):
    text = _text(value)
    if not text:
        return datetime.max.replace(tzinfo=timezone.utc)

    for fmt in (
        "%d-%b-%Y",
        "%d%b%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(text.upper(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    m = re.search(r"(20\d{2})[-/]?([A-Z]{3})[-/]?(\d{1,2})", text.upper())
    if m:
        try:
            return datetime.strptime(
                f"{m.group(3)}-{m.group(2)}-{m.group(1)}",
                "%d-%b-%Y",
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return datetime.max.replace(tzinfo=timezone.utc)


def _choose_record(records, market):
    if not records:
        return None

    segment = market["neo_exchange_segment"]
    candidates = market.get("neo_symbol_candidates", [])

    filtered = [
        r for r in records
        if not r.get("exchange_segment")
        or _text(r["exchange_segment"]).lower() == segment.lower()
    ] or records

    if segment == "mcx_fo":
        # Prefer futures/current front contract rather than an option.
        futures = [
            r for r in filtered
            if "FUT" in _text(r.get("instrument_type")).upper()
            or _text(r.get("trading_symbol")).upper().endswith("FUT")
        ]
        if futures:
            filtered = futures
        filtered.sort(key=lambda r: _expiry_key(r.get("expiry")))

    # Prefer exact symbol matches.
    wanted = {
        re.sub(r"[^A-Z0-9]", "", x.upper())
        for x in candidates
    }

    exact = []
    for r in filtered:
        symbol = re.sub(
            r"[^A-Z0-9]",
            "",
            _text(r.get("trading_symbol")).upper(),
        )
        if symbol in wanted:
            exact.append(r)

    return (exact or filtered)[0]


def resolve_instrument(symbol):
    canonical = canonical_symbol(symbol)
    cached = _TOKEN_CACHE.get(canonical)
    if cached and time.time() - cached["time"] < _TOKEN_TTL:
        return cached["record"]

    market = get_market(canonical)
    if not market or market.get("provider") != "kotak_neo":
        return None

    record = _search_scrip(market)

    # Index quotes can accept the index display name directly on Neo.
    if record is None and market["asset_class"] == "INDEX":
        record = {
            "instrument_token": market["data_symbol"],
            "exchange_segment": market["neo_exchange_segment"],
            "trading_symbol": market["data_symbol"],
            "expiry": None,
            "instrument_type": "INDEX",
        }

    if record:
        _TOKEN_CACHE[canonical] = {
            "time": time.time(),
            "record": record,
        }

    return record


def _quote_candidates(record, market):
    token = _text(record.get("instrument_token"))
    segment = record.get("exchange_segment") or market["neo_exchange_segment"]

    candidates = []
    if token:
        candidates.append(
            {
                "instrument_token": token,
                "exchange_segment": segment,
            }
        )

    if market["asset_class"] == "INDEX":
        candidates.append(
            {
                "instrument_token": market["data_symbol"],
                "exchange_segment": market["neo_exchange_segment"],
            }
        )

    # de-duplicate
    seen = set()
    out = []
    for item in candidates:
        key = (item["instrument_token"], item["exchange_segment"])
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _extract_quote(response):
    candidates = []

    for obj in _walk_objects(response):
        price = _first(
            obj,
            "ltp",
            "last_traded_price",
            "lastTradedPrice",
            "lastPrice",
            "close",
        )
        if price is None:
            continue

        ohlc = _first(obj, "ohlc", "OHLC") or {}
        if not isinstance(ohlc, dict):
            ohlc = {}

        def val(*keys):
            return _first(obj, *keys) if any(
                k in obj or k.lower() in {str(x).lower() for x in obj}
                for k in keys
            ) else _first(ohlc, *keys)

        candidates.append({
            "price": _to_float(price),
            "open": _to_float(val("open")),
            "high": _to_float(val("high")),
            "low": _to_float(val("low")),
            "close": _to_float(val("close")),
            "volume": _to_float(
                _first(obj, "volume", "last_volume", "volumeTraded")
            ),
            "change": _to_float(
                _first(obj, "change", "net_change", "netChange")
            ),
            "percent_change": _to_float(
                _first(
                    obj,
                    "per_change",
                    "perChange",
                    "net_change_percentage",
                )
            ),
            "instrument_token": _first(
                obj,
                "instrument_token",
                "instrumentToken",
                "exchange_token",
            ),
            "trading_symbol": _first(
                obj,
                "trading_symbol",
                "tradingSymbol",
                "display_symbol",
            ),
        })

    return next(
        (x for x in candidates if x["price"] is not None and x["price"] > 0),
        None,
    )


def _to_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def get_quote(symbol):
    canonical = canonical_symbol(symbol)
    market = get_market(canonical)
    if not market or market.get("provider") != "kotak_neo":
        return None

    record = resolve_instrument(canonical)
    if not record:
        return None

    client = _client()

    for token in _quote_candidates(record, market):
        try:
            response = client.quotes(
                instrument_tokens=[token],
                quote_type="all",
            )
            quote = _extract_quote(response)
            if quote:
                quote["symbol"] = canonical
                quote["source"] = "kotak_neo"
                return quote
        except Exception as exc:
            logger.warning("KOTAK quote failed %s: %s", canonical, exc)

    return None


def get_current_price(symbol):
    quote = get_quote(symbol)
    if not quote:
        return None
    return quote.get("price")


def _interval_candidates(resolution):
    return {
        "5m": ["5m", "5minute", "5 min"],
        "15m": ["15m", "15minute", "15 min"],
        "1h": ["60m", "1h", "60minute", "60 min"],
        "1d": ["1d", "day", "1day"],
    }.get(resolution, [resolution])


def _call_historical(client, segment, token, from_dt, to_dt, resolution):
    fn = getattr(client, "historical_data", None)
    if not callable(fn):
        raise RuntimeError("Installed Kotak Neo SDK has no historical_data().")

    signature = inspect.signature(fn)
    params = signature.parameters

    for interval in _interval_candidates(resolution):
        kwargs = {}

        for name, param in params.items():
            n = name.lower()

            if n in ("exchange_segment", "exchange_segment_code", "segment"):
                kwargs[name] = segment
            elif n in (
                "instrument_token",
                "instrumenttoken",
                "scrip_token",
                "scripcode",
                "scrip_code",
                "token",
            ):
                kwargs[name] = token
            elif n in ("from_date", "fromdate", "start_date", "start"):
                kwargs[name] = from_dt.strftime("%Y-%m-%d %H:%M:%S")
            elif n in ("to_date", "todate", "end_date", "end"):
                kwargs[name] = to_dt.strftime("%Y-%m-%d %H:%M:%S")
            elif n in ("interval", "timeframe", "time_frame", "resolution"):
                kwargs[name] = interval
            elif n in ("oi", "open_interest"):
                kwargs[name] = True

        required = [
            p for p in params.values()
            if p.default is inspect.Parameter.empty
            and p.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        ]

        if all(p.name in kwargs for p in required):
            try:
                return fn(**kwargs)
            except TypeError:
                pass
            except Exception:
                raise

    raise RuntimeError(
        f"Unable to map Kotak historical_data() parameters for {resolution}"
    )


def _extract_candle_rows(response):
    # Most useful shape: {"data": [...]} or {"candles": [...]}
    sequences = []

    if isinstance(response, list):
        sequences.append(response)

    for obj in _walk_objects(response):
        for key in (
            "candles",
            "data",
            "result",
            "historicalData",
            "historical_data",
        ):
            value = obj.get(key)
            if isinstance(value, list):
                sequences.append(value)

    # Prefer a sequence containing candle-like rows.
    for seq in sequences:
        if not seq:
            continue
        first = seq[0]
        if isinstance(first, dict):
            rows = []
            for item in seq:
                ts = _first(
                    item,
                    "timestamp",
                    "time",
                    "date",
                    "datetime",
                    "candle_time",
                )
                rows.append({
                    "timestamp": ts,
                    "open": _first(item, "open", "o"),
                    "high": _first(item, "high", "h"),
                    "low": _first(item, "low", "l"),
                    "close": _first(item, "close", "c"),
                    "volume": _first(item, "volume", "v"),
                })
            return rows

        if isinstance(first, (list, tuple)) and len(first) >= 5:
            return [
                {
                    "timestamp": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5] if len(row) > 5 else 0,
                }
                for row in seq
                if isinstance(row, (list, tuple)) and len(row) >= 5
            ]

    return []


def _candles_to_df(response):
    rows = _extract_candle_rows(response)
    if not rows:
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"]
        )

    df = pd.DataFrame(rows)

    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    # Some APIs return epoch seconds/milliseconds as numbers. Retry those.
    if ts.isna().all():
        raw = pd.to_numeric(df["timestamp"], errors="coerce")
        if raw.notna().any():
            unit = "ms" if raw.dropna().median() > 10_000_000_000 else "s"
            ts = pd.to_datetime(raw, errors="coerce", unit=unit, utc=True)

    df["timestamp"] = ts
    df.dropna(
        subset=["timestamp", "open", "high", "low", "close"],
        inplace=True,
    )
    df.sort_values("timestamp", inplace=True)
    df.drop_duplicates(subset=["timestamp"], keep="last", inplace=True)
    df.set_index("timestamp", inplace=True)

    if "volume" not in df.columns:
        df["volume"] = 0.0

    return df[["open", "high", "low", "close", "volume"]]


def get_history(symbol, resolution="5m", limit=200):
    canonical = canonical_symbol(symbol)
    market = get_market(canonical)

    if not market or market.get("provider") != "kotak_neo":
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"]
        )

    record = resolve_instrument(canonical)
    if not record:
        logger.warning("KOTAK instrument not found for %s", canonical)
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"]
        )

    client = _maybe_authenticate()

    interval_seconds = {
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "1d": 86400,
    }.get(resolution)

    if interval_seconds is None:
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"]
        )

    to_dt = datetime.now(timezone.utc)
    from_dt = to_dt - timedelta(seconds=int(limit) * interval_seconds)

    token = record.get("instrument_token")
    segment = record.get("exchange_segment") or market["neo_exchange_segment"]

    try:
        response = _call_historical(
            client,
            segment,
            token,
            from_dt,
            to_dt,
            resolution,
        )
        df = _candles_to_df(response)
        if not df.empty:
            return df.tail(int(limit))

        logger.warning("KOTAK returned no candles for %s %s", canonical, resolution)
    except Exception as exc:
        logger.warning(
            "KOTAK history failed %s %s: %s",
            canonical,
            resolution,
            exc,
        )

    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume"]
    )


def reset_client():
    global _CLIENT
    with _CLIENT_LOCK:
        _CLIENT = None
    _TOKEN_CACHE.clear()
