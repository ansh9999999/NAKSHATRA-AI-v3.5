"""
NAKSHATRA AI - Kotak Neo market-data adapter.

Drop-in replacement for kotak_neo.py.

Supports:
- Indian live quotes
- NSE/BSE indices
- NSE/BSE/derivative instrument discovery
- Historical candles using Kotak Neo SDK v3.x
- MCX front-contract discovery for live quotes

No order placement is implemented here.
"""

from __future__ import annotations

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
except Exception as exc:
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

    if KOTAK_ACCESS_TOKEN:
        kwargs["access_token"] = KOTAK_ACCESS_TOKEN

    if KOTAK_NEO_FIN_KEY:
        kwargs["neo_fin_key"] = KOTAK_NEO_FIN_KEY

    return NeoAPI(**kwargs)


def _client():
    global _CLIENT

    if not KOTAK_CONSUMER_KEY:
        raise RuntimeError(
            "KOTAK_CONSUMER_KEY is missing in Render Environment."
        )

    with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = _make_client()
        return _CLIENT


def _maybe_authenticate():
    client = _client()

    if KOTAK_ACCESS_TOKEN:
        return client

    if not (
        KOTAK_TOTP_SECRET
        and KOTAK_MOBILE_NUMBER
        and KOTAK_UCC
        and KOTAK_MPIN
    ):
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
        logger.warning(
            "KOTAK NEO authentication unavailable: %s",
            exc,
        )

    return client


# ==========================================================
# GENERIC RESPONSE HELPERS
# ==========================================================

def _walk_objects(value):
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

        value = lower.get(str(key).lower())
        if value not in (None, ""):
            return value

    return None


def _to_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


# ==========================================================
# SCRIPT / INSTRUMENT DISCOVERY
# ==========================================================

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
        _text(
            _first(
                record,
                "trading_symbol",
                "tradingSymbol",
                "display_symbol",
            )
        ),
        _text(_first(record, "symbol", "name")),
    ]

    wanted = [
        re.sub(r"[^A-Z0-9]", "", x.upper())
        for x in candidates
    ]

    for value in values:
        normal = re.sub(r"[^A-Z0-9]", "", value.upper())

        for wanted_symbol in wanted:
            if (
                normal == wanted_symbol
                or normal.startswith(wanted_symbol)
            ):
                return True

    return False


def _extract_search_records(response):
    records = []

    for obj in _walk_objects(response):
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
            return datetime.strptime(
                text.upper(),
                fmt,
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
        r
        for r in records
        if (
            not r.get("exchange_segment")
            or _text(r["exchange_segment"]).lower()
            == segment.lower()
        )
    ] or records

    if segment == "mcx_fo":
        futures = [
            r
            for r in filtered
            if (
                "FUT"
                in _text(r.get("instrument_type")).upper()
                or _text(r.get("trading_symbol")).upper().endswith("FUT")
            )
        ]

        if futures:
            filtered = futures

        filtered.sort(
            key=lambda r: _expiry_key(r.get("expiry"))
        )

    wanted = {
        re.sub(r"[^A-Z0-9]", "", candidate.upper())
        for candidate in candidates
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
                    urls.extend(
                        str(x)
                        for x in value
                        if str(x).startswith("http")
                    )

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
                raw = {str(k): row[k] for k in df.columns}
                normal = _normalise_record(raw)

                if normal["instrument_token"] is None:
                    continue

                if _looks_like_symbol(raw, candidates):
                    records.append(normal)

            if records:
                return _choose_record(records, market)

        except Exception as exc:
            logger.warning(
                "KOTAK scrip master read failed: %s",
                exc,
            )

    return None


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
                    logger.debug(
                        "KOTAK search_scrip failed %s: %s",
                        candidate,
                        exc,
                    )

    return _search_scrip_master(client, market)


def resolve_instrument(symbol):
    canonical = canonical_symbol(symbol)

    cached = _TOKEN_CACHE.get(canonical)

    if (
        cached
        and time.time() - cached["time"] < _TOKEN_TTL
    ):
        return cached["record"]

    market = get_market(canonical)

    if (
        not market
        or market.get("provider") != "kotak_neo"
    ):
        return None

    record = _search_scrip(market)

    if (
        record is None
        and market.get("asset_class") == "INDEX"
    ):
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


# ==========================================================
# LIVE QUOTES
# ==========================================================

def _quote_candidates(record, market):
    token = _text(record.get("instrument_token"))

    segment = (
        record.get("exchange_segment")
        or market["neo_exchange_segment"]
    )

    candidates = []

    if token:
        candidates.append(
            {
                "instrument_token": token,
                "exchange_segment": segment,
            }
        )

    if market.get("asset_class") == "INDEX":
        candidates.append(
            {
                "instrument_token": market["data_symbol"],
                "exchange_segment": market["neo_exchange_segment"],
            }
        )

    output = []
    seen = set()

    for item in candidates:
        key = (
            item["instrument_token"],
            item["exchange_segment"],
        )

        if key not in seen:
            seen.add(key)
            output.append(item)

    return output


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

        def value(*keys):
            direct = _first(obj, *keys)
            if direct is not None:
                return direct
            return _first(ohlc, *keys)

        candidates.append(
            {
                "price": _to_float(price),
                "open": _to_float(value("open")),
                "high": _to_float(value("high")),
                "low": _to_float(value("low")),
                "close": _to_float(value("close")),
                "volume": _to_float(
                    _first(
                        obj,
                        "volume",
                        "last_volume",
                        "volumeTraded",
                    )
                ),
                "change": _to_float(
                    _first(
                        obj,
                        "change",
                        "net_change",
                        "netChange",
                    )
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
            }
        )

    return next(
        (
            x
            for x in candidates
            if (
                x["price"] is not None
                and x["price"] > 0
            )
        ),
        None,
    )


def get_quote(symbol):
    canonical = canonical_symbol(symbol)
    market = get_market(canonical)

    if (
        not market
        or market.get("provider") != "kotak_neo"
    ):
        return None

    record = resolve_instrument(canonical)

    if not record:
        logger.warning(
            "KOTAK instrument not found for %s",
            canonical,
        )
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
            logger.warning(
                "KOTAK quote failed %s: %s",
                canonical,
                exc,
            )

    return None


def get_current_price(symbol):
    quote = get_quote(symbol)

    if not quote:
        return None

    return quote.get("price")


# ==========================================================
# HISTORICAL DATA
# ==========================================================

def _interval_for_resolution(resolution):
    """
    Current Kotak Neo SDK v3.x intervals:
    1min, 3min, 5min, 10min, 15min,
    30min, 60min, D, W
    """
    return {
        "5m": "5min",
        "15m": "15min",
        "1h": "60min",
        "1d": "D",
        "1w": "W",
    }.get(
        str(resolution).lower().strip()
    )


def _max_history_days(resolution):
    return {
        "5m": 30,
        "15m": 60,
        "1h": 90,
        "1d": 180,
        "1w": 180,
    }.get(
        str(resolution).lower().strip(),
        30,
    )


def _call_historical(
    client,
    segment,
    token,
    from_dt,
    to_dt,
    resolution,
):
    """
    Kotak Neo SDK v3.x signature:

        client.historical_data(
            neosymbol,
            interval,
            from_date,
            to_date
        )

    Example:
        neosymbol="nse_cm|1333"
        interval="5min"
    """
    fn = getattr(client, "historical_data", None)

    if not callable(fn):
        raise RuntimeError(
            "Installed Kotak Neo SDK has no historical_data()."
        )

    interval = _interval_for_resolution(resolution)

    if not interval:
        raise RuntimeError(
            f"Unsupported Kotak historical interval: {resolution}"
        )

    token_text = _text(token)

    if not token_text:
        raise RuntimeError(
            "Kotak instrument token is missing."
        )

    neosymbol = f"{segment}|{token_text}"

    return fn(
        neosymbol=neosymbol,
        interval=interval,
        from_date=from_dt.strftime("%Y-%m-%d"),
        to_date=to_dt.strftime("%Y-%m-%d"),
    )


def _extract_candle_rows(response):
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

    for sequence in sequences:
        if not sequence:
            continue

        first = sequence[0]

        if isinstance(first, dict):
            rows = []

            for item in sequence:
                rows.append(
                    {
                        "timestamp": _first(
                            item,
                            "timestamp",
                            "time",
                            "date",
                            "datetime",
                            "candle_time",
                        ),
                        "open": _first(item, "open", "o"),
                        "high": _first(item, "high", "h"),
                        "low": _first(item, "low", "l"),
                        "close": _first(item, "close", "c"),
                        "volume": _first(item, "volume", "v"),
                    }
                )

            return rows

        if (
            isinstance(first, (list, tuple))
            and len(first) >= 5
        ):
            return [
                {
                    "timestamp": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5] if len(row) > 5 else 0,
                }
                for row in sequence
                if (
                    isinstance(row, (list, tuple))
                    and len(row) >= 5
                )
            ]

    return []


def _candles_to_df(response):
    rows = _extract_candle_rows(response)

    if not rows:
        return pd.DataFrame(
            columns=[
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

    df = pd.DataFrame(rows)

    for column in (
        "open",
        "high",
        "low",
        "close",
        "volume",
    ):
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    raw_timestamp = df["timestamp"]

    ts = pd.to_datetime(
        raw_timestamp,
        errors="coerce",
        utc=True,
    )

    if ts.isna().all():
        numeric = pd.to_numeric(
            raw_timestamp,
            errors="coerce",
        )

        if numeric.notna().any():
            unit = (
                "ms"
                if numeric.dropna().median()
                > 10_000_000_000
                else "s"
            )

            ts = pd.to_datetime(
                numeric,
                errors="coerce",
                unit=unit,
                utc=True,
            )

    df["timestamp"] = ts

    df.dropna(
        subset=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
        ],
        inplace=True,
    )

    if df.empty:
        return pd.DataFrame(
            columns=[
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

    df.sort_values("timestamp", inplace=True)

    df.drop_duplicates(
        subset=["timestamp"],
        keep="last",
        inplace=True,
    )

    df.set_index("timestamp", inplace=True)

    if "volume" not in df.columns:
        df["volume"] = 0.0

    return df[
        [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    ]


def get_history(
    symbol,
    resolution="5m",
    limit=200,
):
    canonical = canonical_symbol(symbol)
    market = get_market(canonical)

    if (
        not market
        or market.get("provider") != "kotak_neo"
    ):
        return pd.DataFrame(
            columns=[
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

    record = resolve_instrument(canonical)

    if not record:
        logger.warning(
            "KOTAK instrument not found for %s",
            canonical,
        )
        return pd.DataFrame(
            columns=[
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

    client = _maybe_authenticate()

    resolution_key = (
        str(resolution)
        .lower()
        .strip()
    )

    if resolution_key not in {
        "5m",
        "15m",
        "1h",
        "1d",
        "1w",
    }:
        logger.warning(
            "Unsupported Kotak timeframe %s",
            resolution,
        )
        return pd.DataFrame(
            columns=[
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

    max_days = _max_history_days(resolution_key)

    interval_seconds = {
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "1d": 86400,
        "1w": 604800,
    }[resolution_key]

    requested_days = (
        int(limit) * interval_seconds / 86400
    )

    days = min(
        requested_days,
        max_days,
    )

    to_dt = datetime.now(timezone.utc)
    from_dt = to_dt - timedelta(days=days)

    token = record.get("instrument_token")

    segment = (
        record.get("exchange_segment")
        or market["neo_exchange_segment"]
    )

    try:
        response = _call_historical(
            client,
            segment,
            token,
            from_dt,
            to_dt,
            resolution_key,
        )

        df = _candles_to_df(response)

        if not df.empty:
            df = df.tail(int(limit))

            logger.info(
                "KOTAK HISTORY OK %s %s rows=%s",
                canonical,
                resolution_key,
                len(df),
            )

            return df

        logger.warning(
            "KOTAK returned no candles for %s %s",
            canonical,
            resolution_key,
        )

    except Exception as exc:
        logger.warning(
            "KOTAK history failed %s %s: %s",
            canonical,
            resolution_key,
            exc,
        )

    return pd.DataFrame(
        columns=[
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )


def reset_client():
    global _CLIENT

    with _CLIENT_LOCK:
        _CLIENT = None

    _TOKEN_CACHE.clear()
